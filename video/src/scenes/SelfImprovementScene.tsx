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

const LOOP_STEPS = [
  { label: "Inspect", color: COLORS.edited },
  { label: "Diagnose", color: COLORS.exceeds },
  { label: "Generate", color: COLORS.aligned },
  { label: "Retrain", color: COLORS.accent },
  { label: "Evaluate", color: COLORS.edited },
];

export const SelfImprovementScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });
  const cx = 860;
  const cy = 530;
  const radius = 240;
  const stepDelay = 45;
  const startAt = 25;

  // Rotation highlight sweep
  const sweepStart = startAt + LOOP_STEPS.length * stepDelay + 20;
  const rotAngle = interpolate(
    frame,
    [sweepStart, 420],
    [0, Math.PI * 2.4],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

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

      {/* Center hub */}
      <div
        style={{
          position: "absolute",
          left: cx - 65,
          top: cy - 65,
          width: 130,
          height: 130,
          borderRadius: "50%",
          backgroundColor: COLORS.surface,
          border: `3px solid ${COLORS.accent}`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity: titleProgress,
        }}
      >
        <span style={{ fontSize: 20, fontWeight: 700, color: COLORS.accent }}>W&B</span>
        <span style={{ fontSize: 13, color: COLORS.muted }}>MCP</span>
      </div>

      {/* Circle nodes */}
      {LOOP_STEPS.map((step, i) => {
        const angle = (i / LOOP_STEPS.length) * Math.PI * 2 - Math.PI / 2;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);

        const progress = spring({
          frame: frame - (startAt + i * stepDelay),
          fps,
          config: SPRING_SNAPPY,
        });

        // Highlight logic
        const stepAngle = (i / LOOP_STEPS.length) * Math.PI * 2;
        const diff = Math.abs(((rotAngle + Math.PI * 0.5) % (Math.PI * 2)) - stepAngle);
        const lit = frame > sweepStart && diff < 0.7;

        return (
          <div
            key={step.label}
            style={{
              position: "absolute",
              left: x - 60,
              top: y - 42,
              width: 120,
              height: 84,
              borderRadius: 16,
              backgroundColor: lit ? step.color : COLORS.surface,
              border: `2px solid ${step.color}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: progress,
              transform: `scale(${0.7 + 0.3 * progress}${lit ? " scale(1.08)" : ""})`,
            }}
          >
            <span
              style={{
                fontSize: 17,
                fontWeight: 700,
                color: lit ? COLORS.bg : step.color,
              }}
            >
              {step.label}
            </span>
          </div>
        );
      })}

      {/* Arc arrows */}
      {LOOP_STEPS.map((_, i) => {
        const a1 = (i / LOOP_STEPS.length) * Math.PI * 2 - Math.PI / 2;
        const a2 = (((i + 1) % LOOP_STEPS.length) / LOOP_STEPS.length) * Math.PI * 2 - Math.PI / 2;
        const mid = (a1 + a2) / 2;
        const ax = cx + (radius - 40) * Math.cos(mid);
        const ay = cy + (radius - 40) * Math.sin(mid);

        const prog = spring({
          frame: frame - (startAt + i * stepDelay + 25),
          fps,
          config: SPRING_SMOOTH,
        });

        return (
          <div
            key={`a${i}`}
            style={{
              position: "absolute",
              left: ax - 8,
              top: ay - 8,
              fontSize: 18,
              color: COLORS.subtle,
              opacity: prog,
              transform: `rotate(${(mid * 180) / Math.PI + 90}deg)`,
            }}
          >
            ▾
          </div>
        );
      })}

      {/* Accuracy readout */}
      <div
        style={{
          position: "absolute",
          right: 140,
          top: 200,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          opacity: accProgress,
        }}
      >
        <span style={{ fontSize: 16, color: COLORS.muted, letterSpacing: "0.06em", textTransform: "uppercase" }}>
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
