import React from "react";
import {
  AbsoluteFill,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { COLORS, SPRING_SNAPPY, SPRING_BOUNCY } from "../lib/constants";
import { FadeIn } from "../components/FadeIn";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

const DocBlock: React.FC<{
  label: string;
  color: string;
  delay: number;
  fromX: number;
}> = ({ label, color, delay, fromX }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: SPRING_SNAPPY,
  });

  const x = interpolate(progress, [0, 1], [fromX, 0]);

  return (
    <div
      style={{
        opacity: progress,
        transform: `translateX(${x}px)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 24,
      }}
    >
      <div
        style={{
          width: 200,
          height: 260,
          borderRadius: 16,
          backgroundColor: COLORS.surface,
          border: `2px solid ${color}`,
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          padding: 28,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        {[1, 0.7, 0.85, 0.6, 0.9, 0.5].map((w, i) => (
          <div
            key={i}
            style={{
              height: 8,
              width: `${w * 100}%`,
              backgroundColor: color,
              opacity: 0.4,
              borderRadius: 4,
            }}
          />
        ))}
      </div>
      <span
        style={{
          fontSize: 24,
          fontWeight: 700,
          color,
          letterSpacing: "-0.01em",
        }}
      >
        {label}
      </span>
    </div>
  );
};

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const vsProgress = spring({
    frame: frame - 50,
    fps,
    config: SPRING_BOUNCY,
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
        gap: 56,
      }}
    >
      <FadeIn>
        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: COLORS.white,
            letterSpacing: "-0.02em",
          }}
        >
          Policy <span style={{ color: COLORS.muted }}>vs</span> Law
        </div>
      </FadeIn>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 100,
        }}
      >
        <DocBlock label="HR Policy" color={COLORS.edited} delay={20} fromX={-300} />

        <div
          style={{
            fontSize: 100,
            fontWeight: 700,
            color: COLORS.accent,
            opacity: vsProgress,
            transform: `scale(${vsProgress}) rotate(${(1 - vsProgress) * 10}deg)`,
          }}
        >
          ?
        </div>

        <DocBlock label="CA + Federal" color={COLORS.accent} delay={20} fromX={300} />
      </div>

      <FadeIn delay={100}>
        <div
          style={{
            fontSize: 22,
            color: COLORS.muted,
            letterSpacing: "0.04em",
          }}
        >
          2+ lawyers, weeks of review, inconsistent results
        </div>
      </FadeIn>
    </AbsoluteFill>
  );
};
