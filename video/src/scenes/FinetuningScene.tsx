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

const Card: React.FC<{
  label: string;
  value: string;
  color: string;
  delay: number;
}> = ({ label, value, color, delay }) => {
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
        transform: `translateX(${(1 - progress) * -60}px)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "28px 40px",
        backgroundColor: COLORS.surface,
        borderRadius: 16,
        borderLeft: `4px solid ${color}`,
        border: `1px solid ${COLORS.border}`,
        borderLeftWidth: 4,
        borderLeftColor: color,
        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        width: 560,
      }}
    >
      <span style={{ fontSize: 22, color: COLORS.muted }}>{label}</span>
      <span
        style={{
          fontSize: 26,
          fontWeight: 700,
          color,
          fontFamily: monoFamily,
        }}
      >
        {value}
      </span>
    </div>
  );
};

const LossChart: React.FC<{ delay: number }> = ({ delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 60,
  });

  const w = 340;
  const h = 180;
  const points: [number, number][] = [
    [0, 164],
    [w * 0.12, 120],
    [w * 0.25, 80],
    [w * 0.4, 52],
    [w * 0.55, 34],
    [w * 0.7, 22],
    [w * 0.85, 16],
    [w, 12],
  ];

  const clipWidth = w * progress;

  return (
    <div
      style={{
        opacity: progress,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
      }}
    >
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <defs>
          <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={COLORS.accent} stopOpacity={0.3} />
            <stop offset="100%" stopColor={COLORS.accent} stopOpacity={0} />
          </linearGradient>
          <clipPath id="lossClip">
            <rect x={0} y={0} width={clipWidth} height={h} />
          </clipPath>
        </defs>
        {/* Fill area */}
        <g clipPath="url(#lossClip)">
          <path
            d={`M ${points.map(([x, y]) => `${x},${h - y}`).join(" L ")} L ${w},${h} L 0,${h} Z`}
            fill="url(#lossGrad)"
          />
          <polyline
            points={points.map(([x, y]) => `${x},${h - y}`).join(" ")}
            fill="none"
            stroke={COLORS.accent}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
        {/* Baseline */}
        <line
          x1={0} y1={h - 1} x2={w} y2={h - 1}
          stroke={COLORS.subtle}
          strokeWidth={1}
        />
      </svg>
      <span style={{ fontSize: 15, color: COLORS.muted, fontFamily: monoFamily }}>
        loss ↓
      </span>
    </div>
  );
};

export const FinetuningScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  const feedbackProgress = spring({
    frame: frame - 271,
    fps,
    config: SPRING_SNAPPY,
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
        gap: 36,
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
        Fine-Tuning
      </div>

      <div style={{ display: "flex", gap: 80, alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card label="Model" value="Mistral 7B" color={COLORS.accent} delay={11} />
          <Card label="Method" value="QLoRA 4-bit" color={COLORS.exceeds} delay={41} />
          <Card label="Data" value="500+ pairs" color={COLORS.aligned} delay={71} />
          <Card label="Tracking" value="W&B" color={COLORS.edited} delay={101} />
        </div>

        <LossChart delay={131} />
      </div>

      {/* Feedback loop */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          opacity: feedbackProgress,
          transform: `translateY(${(1 - feedbackProgress) * 20}px)`,
          padding: "16px 36px",
          borderRadius: 12,
          border: `1px dashed ${COLORS.subtle}`,
        }}
      >
        <span style={{ fontSize: 20, color: COLORS.muted }}>
          Lawyer edits
        </span>
        <span style={{ fontSize: 24, color: COLORS.accent }}>→</span>
        <span style={{ fontSize: 20, fontWeight: 700, color: COLORS.accent }}>
          retrain
        </span>
      </div>
    </AbsoluteFill>
  );
};
