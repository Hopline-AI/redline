import { useState } from "react";
import type { ReviewStatus } from "@/types";
import { CheckCircle2, Flag } from "lucide-react";

interface Props {
  currentStatus: ReviewStatus;
  onApprove: (notes?: string) => void;
  onReject: (notes?: string) => void;
  onEdit: () => void;
  isEditing: boolean;
}

export function ReviewActions({ currentStatus, onApprove, onReject, onEdit, isEditing }: Props) {
  const [notes, setNotes] = useState("");

  return (
    <div className="review-actions">
      <input
        type="text"
        className="notes-input"
        placeholder="Optional notes..."
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{ margin: 0, padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px" }}
      />
      <button
        className="btn-danger"
        onClick={() => {
          onReject(notes || undefined);
          setNotes("");
        }}
        disabled={currentStatus === "rejected"}
        style={currentStatus === "rejected" ? { opacity: 0.5 } : { backgroundColor: "var(--danger)", color: "white", border: "none" }}
      >
        Reject
      </button>
      <button
        className="btn-secondary"
        onClick={onEdit}
        style={isEditing ? { backgroundColor: "var(--bg-3)" } : {}}
      >
        Edit
      </button>
      <button
        className="btn-primary"
        onClick={() => {
          onApprove(notes || undefined);
          setNotes("");
        }}
        disabled={currentStatus === "approved"}
        style={
          currentStatus === "approved"
            ? { opacity: 0.5, backgroundColor: "var(--success)", color: "white", border: "none" }
            : { backgroundColor: "var(--success)", color: "white", border: "none" }
        }
      >
        <CheckCircle2 size={14} />
        Approve
      </button>
    </div>
  );
}
