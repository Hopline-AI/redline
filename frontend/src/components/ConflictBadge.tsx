import type { ConflictType } from "@/types";
import {
  AlertTriangle,
  XCircle,
  ArrowDown,
  ArrowUp,
  HelpCircle,
  CheckCircle2,
} from "lucide-react";

const LABELS: Record<ConflictType, string> = {
  contradicts: "Contradicts",
  falls_short: "Falls Short",
  exceeds: "Exceeds",
  missing: "Missing",
  aligned: "Aligned",
};

const ICONS: Record<ConflictType, React.ReactNode> = {
  contradicts: <XCircle size={12} />,
  falls_short: <ArrowDown size={12} />,
  exceeds: <ArrowUp size={12} />,
  missing: <HelpCircle size={12} />,
  aligned: <CheckCircle2 size={12} />,
};

interface Props {
  type: ConflictType;
}

export function ConflictBadge({ type }: Props) {
  return (
    <span className={`conflict-badge ${type}`}>
      {ICONS[type]}
      {LABELS[type]}
    </span>
  );
}

// Utility: get the worst conflict type from a list
export function worstConflict(types: ConflictType[]): ConflictType {
  const severity: ConflictType[] = [
    "contradicts",
    "falls_short",
    "exceeds",
    "missing",
    "aligned",
  ];
  for (const s of severity) {
    if (types.includes(s)) return s;
  }
  return "aligned";
}
