import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, SPRING_SMOOTH } from "../lib/constants";

type FlowArrowProps = {
  delay?: number;
  length?: number;
};

export const FlowArrow: React.FC<FlowArrowProps> = ({
  delay = 0,
  length = 50,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: SPRING_SMOOTH,
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        opacity: progress,
      }}
    >
      <div
        style={{
          width: length * progress,
          height: 2,
          backgroundColor: COLORS.subtle,
        }}
      />
      <div
        style={{
          width: 0,
          height: 0,
          borderLeft: `8px solid ${COLORS.subtle}`,
          borderTop: "5px solid transparent",
          borderBottom: "5px solid transparent",
        }}
      />
    </div>
  );
};
