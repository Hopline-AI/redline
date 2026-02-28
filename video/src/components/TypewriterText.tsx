import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

type TypewriterTextProps = {
  text: string;
  delay?: number;
  charFrames?: number;
  style?: React.CSSProperties;
};

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  delay = 0,
  charFrames = 2,
  style,
}) => {
  const frame = useCurrentFrame();
  const adjustedFrame = Math.max(0, frame - delay);
  const charCount = Math.min(text.length, Math.floor(adjustedFrame / charFrames));

  const cursorOpacity = interpolate(
    frame % 16,
    [0, 8, 16],
    [1, 0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <span style={style}>
      {text.slice(0, charCount)}
      {charCount < text.length && (
        <span style={{ opacity: cursorOpacity, color: "#ef5350" }}>|</span>
      )}
    </span>
  );
};
