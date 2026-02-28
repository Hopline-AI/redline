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
import { TypewriterText } from "../components/TypewriterText";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: SPRING_SMOOTH });
  const lineWidth = spring({
    frame: frame - 8,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 30,
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
      }}
    >
      {/* Accent line above title */}
      <div
        style={{
          width: interpolate(lineWidth, [0, 1], [0, 120]),
          height: 4,
          backgroundColor: COLORS.accent,
          borderRadius: 2,
          marginBottom: 32,
        }}
      />

      <div
        style={{
          fontSize: 160,
          fontWeight: 700,
          color: COLORS.white,
          opacity: titleScale,
          transform: `scale(${0.9 + 0.1 * titleScale})`,
          letterSpacing: "-0.03em",
          lineHeight: 1,
        }}
      >
        Red<span style={{ color: COLORS.accent }}>line</span>
      </div>

      <div
        style={{
          fontSize: 28,
          color: COLORS.muted,
          marginTop: 24,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          height: 36,
        }}
      >
        <TypewriterText text="Compliance Engine" delay={15} charFrames={3} />
      </div>
    </AbsoluteFill>
  );
};
