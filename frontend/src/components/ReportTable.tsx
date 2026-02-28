import React from 'react';
import { ConflictBadge } from "@/components/ConflictBadge";
import { worstConflict } from "@/utils/conflictUtils";

interface Props {
  rules: any[];
}

export function ReportTable({ rules }: Props) {
  return (
    <div className="table">
      <table>
        <thead>
          <tr>
            <th>Rule ID</th>
            <th>Type</th>
            <th>Worst Conflict</th>
            <th>Status</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule) => {
            const conflictTypes = rule.conflicts.map((c: any) => c.conflict_type);
            const worst = conflictTypes.length > 0 ? worstConflict(conflictTypes) : null;
            return (
              <tr key={rule.rule_id}>
                <td>
                  <code>{rule.rule_id}</code>
                </td>
                <td>
                  <span className="type-badge">{rule.rule_type}</span>
                </td>
                <td>{worst ? <ConflictBadge type={worst as any} /> : <span className="text-light">—</span>}</td>
                <td>
                  <span className={`status-badge ${rule.status}`}>{rule.status}</span>
                </td>
                <td>
                  <small className="text-light">{rule.lawyer_notes ?? "—"}</small>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
