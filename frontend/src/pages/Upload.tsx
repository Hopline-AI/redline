import { useState, useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FileUpload } from "@/components/FileUpload";
import { Stepper } from "@/components/Stepper";
import { uploadPolicy, pollPipeline } from "@/api/client";
import { FileText } from "lucide-react";

export default function Upload() {
  const { policyId: urlPolicyId } = useParams<{ policyId?: string }>();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [policyId, setPolicyId] = useState<string | null>(urlPolicyId ?? null);

  const { mutate: doUpload, isPending: isUploading } = useMutation({
    mutationFn: uploadPolicy,
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
    queryFn: () => pollPipeline(policyId!),
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

  return (
    <div className="upload-page">
      <div className="upload-hero">
        <h1>Upload Policy Document</h1>
        <p className="text-light">
          Upload your company's HR policy (PDF) and we'll extract decision rules,
          then compare them against California and Federal employment legislation.
        </p>
      </div>

      {!file && !policyId ? (
        <FileUpload onFile={handleFile} disabled={isUploading} />
      ) : (
        <div style={{ width: "100%", maxWidth: 500, textAlign: "center" }}>
          {/* File info */}
          {file ? (
            <div className="card mb-4 hstack gap-2" style={{ justifyContent: "center" }}>
              <FileText size={18} />
              <span style={{ fontSize: "var(--text-7)" }}>{file.name}</span>
              <small className="text-light">
                ({(file.size / 1024).toFixed(0)} KB)
              </small>
            </div>
          ) : (
            <div className="card mb-4 hstack gap-2" style={{ justifyContent: "center" }}>
              <FileText size={18} />
              <span style={{ fontSize: "var(--text-7)" }}>Processing Job: {policyId}</span>
            </div>
          )}

          {/* Stepper */}
          {(progress || isUploading) && (
            <Stepper
              currentPhase={progress ? progress.phase : "upload"}
              status={progress ? (progress.status === "queued" ? "processing" : progress.status) : "processing"}
            />
          )}

          {/* Progress bar */}
          {progress && progress.status !== "complete" && (
            <progress value={progress.progress} max={100} style={{ marginTop: "var(--space-4)" }} />
          )}

          {progress?.status === "complete" && (
            <div role="alert" data-variant="success" style={{ marginTop: "var(--space-4)" }}>
              Extraction complete! Redirecting to review...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
