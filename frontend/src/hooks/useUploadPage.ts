import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { uploadPolicy, pollPipeline } from "@/api/client";
import { storePdf } from "@/utils/indexedDB";

export function useUploadPage(urlPolicyId: string | undefined) {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [policyId, setPolicyId] = useState<string | null>(urlPolicyId ?? null);

    const { mutate: doUpload, isPending: isUploading } = useMutation({
        mutationFn: async (f: File) => {
            const res = await uploadPolicy(f);
            await storePdf(res.policyId, f);
            return res;
        },
        onSuccess: (res) => {
            setPolicyId(res.policyId);
            navigate(`/${res.policyId}`, { replace: true });
        },
        onError: (err: any) => {
            alert("Upload failed: " + err.message);
        }
    });

    const handleFile = useCallback(
        (f: File) => {
            setFile(f);
            doUpload(f);
        },
        [doUpload]
    );

    const { data: progress } = useQuery({
        queryKey: ['pipelineProgress', policyId],
        queryFn: () => {
            if (!policyId) throw new Error("No policy ID provided");
            return pollPipeline(policyId);
        },
        enabled: !!policyId,
        refetchInterval: (query) => {
            const data = query.state.data;
            if (!data) return 2000;
            if (data.status === "complete" || data.status === "error") {
                return false;
            }
            if (data.phase === "extract") return 5000;
            if (data.phase === "upload" || data.phase === "parse") return 1000;
            return 2000;
        },
    });

    useEffect(() => {
        if (progress?.status === "complete") {
            const t = setTimeout(() => navigate(`/review/${policyId}`), 600);
            return () => clearTimeout(t);
        }
    }, [progress?.status, policyId, navigate]);

    return { file, policyId, isUploading, handleFile, progress };
}
