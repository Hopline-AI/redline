import React from "react";
import {
  AbsoluteFill,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { COLORS, SPRING_SMOOTH } from "../lib/constants";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

export const ClosingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });
  const lineWidth = spring({
    frame: frame - 10,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 30,
  });
  const tagProgress = spring({ frame: frame - 20, fps, config: SPRING_SMOOTH });

  const fadeOut = interpolate(frame, [120, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily,
        gap: 24,
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          fontSize: 180,
          fontWeight: 700,
          color: COLORS.white,
          opacity: titleProgress,
          transform: `scale(${0.92 + 0.08 * titleProgress})`,
          letterSpacing: "-0.04em",
          lineHeight: 1,
        }}
      >
        Red<span style={{ color: COLORS.accent }}>line</span>
      </div>

      {/* Accent line */}
      <div
        style={{
          width: interpolate(lineWidth, [0, 1], [0, 160]),
          height: 3,
          backgroundColor: COLORS.accent,
          borderRadius: 2,
        }}
      />

      <div
        style={{
          fontSize: 26,
          color: COLORS.muted,
          opacity: tagProgress,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          marginTop: 8,
        }}
      >
        Compliance you can explain
      </div>
    </AbsoluteFill>
  );
};
