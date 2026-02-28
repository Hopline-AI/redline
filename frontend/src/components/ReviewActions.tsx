import { useState } from "react";
import type { ReviewStatus } from "@/types";
import { CheckCircle2, Flag } from "lucide-react";

interface Props {
  currentStatus: ReviewStatus;
  onApprove: (notes?: string) => void;
  onFlag: (notes?: string) => void;
}

export function ReviewActions({ currentStatus, onApprove, onFlag }: Props) {
  const [notes, setNotes] = useState("");

  return (
    <div className="review-actions">
      <input
        type="text"
        className="notes-input"
        placeholder="Optional notes..."
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{ margin: 0 }}
      />
      <button
        data-variant="secondary"
        onClick={() => {
          onFlag(notes || undefined);
          setNotes("");
        }}
        disabled={currentStatus === "flagged"}
        style={currentStatus === "flagged" ? { opacity: 0.5 } : {}}
      >
        <Flag size={14} />
        Flag
      </button>
      <button
        onClick={() => {
          onApprove(notes || undefined);
          setNotes("");
        }}
        disabled={currentStatus === "approved"}
        style={
          currentStatus === "approved"
            ? { opacity: 0.5 }
            : { backgroundColor: "var(--success)", borderColor: "var(--success)" }
        }
      >
        <CheckCircle2 size={14} />
        Approve
      </button>
    </div>
  );
}
