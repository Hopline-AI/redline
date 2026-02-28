import { useParams } from "react-router-dom";
import { FileUpload } from "@/components/FileUpload";
import { Stepper } from "@/components/Stepper";
import { SEO } from "@/components/SEO";
import { FileText } from "lucide-react";
import { useUploadPage } from "@/hooks/useUploadPage";
import { LawDisclaimerToast } from "@/components/LawDisclaimerToast";

export default function Upload() {
  const { policyId: urlPolicyId } = useParams<{ policyId?: string }>();
  
  const { file, policyId, isUploading, handleFile, progress } = useUploadPage(urlPolicyId);

  return (
    <div className="upload-page">
      <SEO 
        title="Upload Policy" 
        description="Upload your HR policy PDF for AI-powered compliance analysis."
      />
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
      <LawDisclaimerToast />
    </div>
  );
}
