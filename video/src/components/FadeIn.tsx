import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { SPRING_SMOOTH } from "../lib/constants";

type FadeInProps = {
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
};

export const FadeIn: React.FC<FadeInProps> = ({
  children,
  delay = 0,
  style,
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
        opacity: progress,
        transform: `translateY(${(1 - progress) * 30}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
