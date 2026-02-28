import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { SPRING_SNAPPY } from "../lib/constants";

type AnimatedBoxProps = {
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
};

export const AnimatedBox: React.FC<AnimatedBoxProps> = ({
  children,
  delay = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: SPRING_SNAPPY,
  });

  return (
    <div
      style={{
        opacity: progress,
        transform: `scale(${0.85 + 0.15 * progress})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
