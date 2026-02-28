import React from "react";
import { Info } from "lucide-react";

export function LawDisclaimerToast() {
  return (
    <div className="law-disclaimer">
      <Info className="icon" size={16} />
      <p>
        <strong>Notice:</strong> This version operates exclusively under California state and Federal laws.
      </p>
    </div>
  );
}
