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

const StatBar: React.FC<{
  label: string;
  value: number;
  color: string;
  delay: number;
  suffix?: string;
}> = ({ label, value, color, delay, suffix = "%" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 50,
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20, width: 480 }}>
      <span
        style={{
          fontSize: 18,
          color: COLORS.muted,
          width: 160,
          textAlign: "right",
        }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: 32,
          backgroundColor: COLORS.border,
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${value * progress}%`,
            backgroundColor: color,
            borderRadius: 8,
          }}
        />
      </div>
      <span
        style={{
          fontSize: 20,
          fontWeight: 700,
          color,
          width: 70,
          fontFamily: monoFamily,
        }}
      >
        {Math.round(value * progress)}{suffix}
      </span>
    </div>
  );
};

const ArchBox: React.FC<{
  title: string;
  detail: string;
  color: string;
  delay: number;
}> = ({ title, detail, color, delay }) => {
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
        padding: "32px 40px",
        backgroundColor: COLORS.surface,
        borderRadius: 16,
        borderLeft: `4px solid ${color}`,
        border: `1px solid ${COLORS.border}`,
        borderLeftWidth: 4,
        borderLeftColor: color,
        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        width: 440,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <span style={{ fontSize: 28, fontWeight: 700, color }}>{title}</span>
      <span style={{ fontSize: 16, color: COLORS.muted, fontFamily: monoFamily }}>
        {detail}
      </span>
    </div>
  );
};

export const ServingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  // Pulsing latency dot
  const dotEntry = spring({ frame: frame - 50, fps, config: SPRING_SNAPPY });
  const pulse = interpolate((frame - 50) % 30, [0, 15, 30], [1, 1.4, 1], {
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
        gap: 40,
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
        Inference
      </div>

      <div style={{ display: "flex", gap: 60, alignItems: "flex-start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <ArchBox title="vLLM" detail="PagedAttention + batching" color={COLORS.accent} delay={10} />
          <ArchBox title="Constrained Decoding" detail="outlines → valid JSON" color={COLORS.aligned} delay={35} />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 12 }}>
          {/* Latency indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 8 }}>
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                backgroundColor: COLORS.aligned,
                opacity: dotEntry,
                transform: `scale(${frame > 50 ? pulse : 0})`,
              }}
            />
            <span style={{ fontSize: 20, color: COLORS.muted }}>
              <span style={{ color: COLORS.aligned, fontWeight: 700, fontFamily: monoFamily }}>
                ~350ms
              </span>{" "}
              p50
            </span>
          </div>

          <StatBar label="GPU util" value={87} color={COLORS.accent} delay={80} />
          <StatBar label="JSON validity" value={100} color={COLORS.aligned} delay={105} />
          <StatBar label="VRAM" value={62} color={COLORS.edited} delay={130} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
