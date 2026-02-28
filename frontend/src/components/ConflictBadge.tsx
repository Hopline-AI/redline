import type { ConflictType } from "@/types";
import {
  AlertTriangle,
  XCircle,
  ArrowDown,
  ArrowUp,
  HelpCircle,
  CheckCircle2,
} from "lucide-react";
import { CONFLICT_LABELS } from "@/utils/conflictUtils";

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
      {CONFLICT_LABELS[type]}
    </span>
  );
}
