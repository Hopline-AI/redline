import React from "react";
import {
  AbsoluteFill,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { COLORS, SPRING_SNAPPY, SPRING_SMOOTH } from "../lib/constants";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});
const { fontFamily: monoFamily } = loadMono("normal", {
  weights: ["400"],
  subsets: ["latin"],
});

const STAIR_STEPS = [
  { label: "Inspect", color: COLORS.edited },
  { label: "Diagnose", color: COLORS.exceeds },
  { label: "Generate", color: COLORS.aligned },
  { label: "Retrain", color: COLORS.accent },
  { label: "Evaluate", color: COLORS.edited },
];

const STEP_DELAY = 50;
const START_AT = 30;

export const SelfImprovementScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  // Staircase layout
  const baseX = 200;
  const baseY = 700;
  const stepWidth = 200;
  const stepRise = 80;

  // Climbing highlight — which step is lit
  const allStepsIn = START_AT + STAIR_STEPS.length * STEP_DELAY + 30;
  const highlightIndex = interpolate(
    frame,
    [allStepsIn, allStepsIn + STAIR_STEPS.length * 40],
    [0, STAIR_STEPS.length - 0.01],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const activeStep = Math.floor(highlightIndex);

  // Accuracy counter
  const accDelay = 180;
  const accProgress = spring({
    frame: frame - accDelay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 150,
  });
  const accuracy = interpolate(accProgress, [0, 1], [71, 94]);

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, fontFamily }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 60,
          width: "100%",
          textAlign: "center",
          fontSize: 56,
          fontWeight: 700,
          color: COLORS.white,
          opacity: titleProgress,
          transform: `translateY(${(1 - titleProgress) * 20}px)`,
          letterSpacing: "-0.03em",
        }}
      >
        Self-Improvement
      </div>

      {/* W&B MCP badge */}
      <div
        style={{
          position: "absolute",
          top: 140,
          width: "100%",
          textAlign: "center",
          opacity: titleProgress,
        }}
      >
        <span
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: COLORS.accent,
            padding: "8px 24px",
            borderRadius: 20,
            border: `2px solid ${COLORS.accent}`,
            backgroundColor: COLORS.surface,
            letterSpacing: "0.04em",
          }}
        >
          W&B MCP Orchestrated
        </span>
      </div>

      {/* Staircase */}
      {STAIR_STEPS.map((step, i) => {
        const stepProgress = spring({
          frame: frame - (START_AT + i * STEP_DELAY),
          fps,
          config: SPRING_SNAPPY,
        });

        const x = baseX + i * stepWidth;
        const y = baseY - (i + 1) * stepRise;
        const platformHeight = (i + 1) * stepRise;

        const isLit = frame >= allStepsIn && activeStep >= i;

        return (
          <React.Fragment key={step.label}>
            {/* Platform/pillar */}
            <div
              style={{
                position: "absolute",
                left: x,
                top: y,
                width: stepWidth - 16,
                height: platformHeight,
                backgroundColor: isLit ? step.color : COLORS.surface,
                borderRadius: "12px 12px 0 0",
                opacity: stepProgress,
                transform: `translateY(${(1 - stepProgress) * 40}px)`,
                transition: "background-color 0.3s",
              }}
            />

            {/* Label on top of platform */}
            <div
              style={{
                position: "absolute",
                left: x,
                top: y - 52,
                width: stepWidth - 16,
                textAlign: "center",
                opacity: stepProgress,
                transform: `translateY(${(1 - stepProgress) * 40}px)`,
              }}
            >
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: isLit ? step.color : COLORS.muted,
                  transition: "color 0.3s",
                }}
              >
                {step.label}
              </span>
            </div>

            {/* Step number inside platform */}
            <div
              style={{
                position: "absolute",
                left: x,
                top: y + 12,
                width: stepWidth - 16,
                textAlign: "center",
                opacity: stepProgress * 0.6,
                transform: `translateY(${(1 - stepProgress) * 40}px)`,
              }}
            >
              <span
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: isLit ? "#1a1a1a" : COLORS.muted,
                  fontFamily: monoFamily,
                }}
              >
                {i + 1}
              </span>
            </div>

            {/* Arrow between steps */}
            {i < STAIR_STEPS.length - 1 && (
              <div
                style={{
                  position: "absolute",
                  left: x + stepWidth - 16,
                  top: y - 20,
                  opacity: spring({
                    frame: frame - (START_AT + i * STEP_DELAY + 30),
                    fps,
                    config: SPRING_SMOOTH,
                  }),
                  fontSize: 22,
                  color: COLORS.subtle,
                  transform: "rotate(-30deg)",
                }}
              >
                →
              </div>
            )}
          </React.Fragment>
        );
      })}

      {/* Climbing ball */}
      {frame >= allStepsIn && (() => {
        const ballX = baseX + activeStep * stepWidth + (stepWidth - 16) / 2 - 14;
        const ballY = baseY - (activeStep + 1) * stepRise - 80;
        const bounceOffset = Math.sin(frame * 0.15) * 4;

        return (
          <div
            style={{
              position: "absolute",
              left: ballX,
              top: ballY + bounceOffset,
              width: 28,
              height: 28,
              borderRadius: "50%",
              backgroundColor: STAIR_STEPS[activeStep].color,
              boxShadow: `0 0 20px ${STAIR_STEPS[activeStep].color}80`,
            }}
          />
        );
      })()}

      {/* Accuracy readout */}
      <div
        style={{
          position: "absolute",
          right: 140,
          top: 240,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          opacity: accProgress,
        }}
      >
        <span
          style={{
            fontSize: 16,
            color: COLORS.muted,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          Accuracy
        </span>
        <span
          style={{
            fontSize: 80,
            fontWeight: 700,
            color: COLORS.aligned,
            fontFamily: monoFamily,
            lineHeight: 1,
          }}
        >
          {accuracy.toFixed(1)}%
        </span>
      </div>
    </AbsoluteFill>
  );
};
