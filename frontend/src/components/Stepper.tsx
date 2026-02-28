import { Check, Loader2 } from "lucide-react";
import type { JobPhase } from "@/types";

const STEPS: { id: JobPhase; label: string }[] = [
  { id: "upload", label: "Upload" },
  { id: "parse", label: "Parse" },
  { id: "extract", label: "Extract" },
  { id: "compare", label: "Compare" },
];

interface Props {
  currentPhase: JobPhase;
  status: "processing" | "complete" | "error";
}

export function Stepper({ currentPhase, status }: Props) {
  const currentIdx = STEPS.findIndex((s) => s.id === currentPhase);
  const isComplete = status === "complete";

  return (
    <div className="stepper">
      {STEPS.map((step, i) => {
        const isDone = isComplete || i < currentIdx;
        const isActive = !isComplete && i === currentIdx;

        return (
          <div key={step.id}>
            <div className="hstack gap-2" style={{ flexWrap: "nowrap" }}>
              <div
                className={`stepper-step ${isDone ? "complete" : isActive ? "active" : "pending"}`}
              >
                <span className="step-icon">
                  {isDone ? (
                    <Check size={12} />
                  ) : isActive ? (
                    <Loader2 size={12} className="spinner" style={{ border: "none", animation: "spin 0.8s linear infinite" }} />
                  ) : (
                    <span style={{ fontSize: "0.6rem" }}>{i + 1}</span>
                  )}
                </span>
                <span>{step.label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`stepper-connector ${isDone ? "complete" : ""}`} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
