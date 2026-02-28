import React from "react";
import {
  AbsoluteFill,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { COLORS, SPRING_SNAPPY, SPRING_SMOOTH } from "../lib/constants";
import { FlowArrow } from "../components/FlowArrow";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});
const { fontFamily: monoFamily } = loadMono("normal", {
  weights: ["400"],
  subsets: ["latin"],
});

const STEPS = [
  { label: "Upload", color: COLORS.edited },
  { label: "Parse", color: COLORS.edited },
  { label: "Extract", color: COLORS.accent },
  { label: "Compare", color: COLORS.exceeds },
  { label: "Report", color: COLORS.aligned },
  { label: "Review", color: COLORS.white },
];

const PipelineStep: React.FC<{
  label: string;
  color: string;
  delay: number;
  isActive: boolean;
}> = ({ label, color, delay, isActive }) => {
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
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 50}px)`,
      }}
    >
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: 24,
          backgroundColor: isActive ? color : COLORS.surface,
          border: `2px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: isActive ? COLORS.bg : color,
            letterSpacing: "-0.01em",
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};

export const PipelineScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  const STEP_INTERVAL = 70;
  const STEP_START = 40;

  // Which step is "active" (highlighted) — sweeps through them
  const activeIndex = Math.min(
    STEPS.length - 1,
    Math.max(-1, Math.floor((frame - STEP_START - STEPS.length * STEP_INTERVAL) / 40)),
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily,
        gap: 64,
      }}
    >
      <div
        style={{
          fontSize: 56,
          fontWeight: 700,
          color: COLORS.white,
          opacity: titleProgress,
          transform: `translateY(${(1 - titleProgress) * 20}px)`,
          letterSpacing: "-0.03em",
        }}
      >
        The Pipeline
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {STEPS.map((step, i) => (
          <React.Fragment key={step.label}>
            <PipelineStep
              label={step.label}
              color={step.color}
              delay={STEP_START + i * STEP_INTERVAL}
              isActive={i === activeIndex}
            />
            {i < STEPS.length - 1 && (
              <FlowArrow delay={STEP_START + i * STEP_INTERVAL + 35} length={36} />
            )}
          </React.Fragment>
        ))}
      </div>

      <Sequence from={STEP_START + 2 * STEP_INTERVAL + 40} layout="none" premountFor={30}>
        {(() => {
          const f = useCurrentFrame();
          const opacity = interpolate(f, [0, 20], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              style={{
                fontSize: 22,
                color: COLORS.muted,
                opacity,
                fontFamily: monoFamily,
                padding: "16px 32px",
                borderRadius: 12,
                border: `1px solid ${COLORS.border}`,
              }}
            >
              AI extracts → deterministic code compares
            </div>
          );
        })()}
      </Sequence>
    </AbsoluteFill>
  );
};
