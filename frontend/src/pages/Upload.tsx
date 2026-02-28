import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { FileUpload } from "@/components/FileUpload";
import { Stepper } from "@/components/Stepper";
import { uploadPolicy, startPipeline, pollPipeline } from "@/data/mockApi";
import type { JobProgress } from "@/types";
import { FileText } from "lucide-react";

export default function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [policyId, setPolicyId] = useState<string | null>(null);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const handleFile = useCallback(
    async (f: File) => {
      setFile(f);

      // Upload
      const res = await uploadPolicy(f);
      setPolicyId(res.policyId);

      // Start pipeline
      startPipeline(res.policyId);
      setProgress({ phase: "upload", status: "processing", progress: 0 });
    },
    []
  );

  // Poll the pipeline
  useEffect(() => {
    if (!policyId || !progress || progress.status === "complete") return;

    pollRef.current = setInterval(async () => {
      const p = await pollPipeline(policyId);
      setProgress(p);

      if (p.status === "complete") {
        clearInterval(pollRef.current);
        // Navigate to review after a brief pause
        setTimeout(() => {
          navigate(`/review/pol_demo_001`);
        }, 600);
      }
    }, 500);

    return () => clearInterval(pollRef.current);
  }, [policyId, progress?.status, navigate]);

  return (
    <div className="upload-page">
      <div className="upload-hero">
        <h1>Upload Policy Document</h1>
        <p className="text-light">
          Upload your company's HR policy (PDF) and we'll extract decision rules,
          then compare them against California and Federal employment legislation.
        </p>
      </div>

      {!file ? (
        <FileUpload onFile={handleFile} />
      ) : (
        <div style={{ width: "100%", maxWidth: 500, textAlign: "center" }}>
          {/* File info */}
          <div className="card mb-4 hstack gap-2" style={{ justifyContent: "center" }}>
            <FileText size={18} />
            <span style={{ fontSize: "var(--text-7)" }}>{file.name}</span>
            <small className="text-light">
              ({(file.size / 1024).toFixed(0)} KB)
            </small>
          </div>

          {/* Stepper */}
          {progress && (
            <Stepper
              currentPhase={progress.phase}
              status={progress.status === "queued" ? "processing" : progress.status}
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
