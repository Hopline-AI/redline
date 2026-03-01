import React from "react";
import {
  AbsoluteFill,
  spring,
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

const SpecRow: React.FC<{
  label: string;
  value: string;
  color: string;
}> = ({ label, value, color }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "10px 0",
      borderBottom: `1px solid ${COLORS.border}`,
    }}
  >
    <span style={{ fontSize: 15, color: COLORS.muted, fontFamily }}>{label}</span>
    <span style={{ fontSize: 15, fontWeight: 700, color, fontFamily: monoFamily }}>
      {value}
    </span>
  </div>
);

const ClusterCard: React.FC<{
  title: string;
  subtitle: string;
  gpu: string;
  vram: string;
  role: string;
  specs: { label: string; value: string }[];
  color: string;
  delay: number;
}> = ({ title, subtitle, gpu, vram, role, specs, color, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({ frame: frame - delay, fps, config: SPRING_SNAPPY });

  return (
    <div
      style={{
        opacity: progress,
        transform: `translateY(${(1 - progress) * 60}px)`,
        backgroundColor: COLORS.surface,
        borderRadius: 20,
        border: `2px solid ${color}`,
        borderTopWidth: 4,
        borderTopColor: color,
        padding: "36px 40px",
        width: 420,
        display: "flex",
        flexDirection: "column",
        gap: 20,
        boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
      }}
    >
      {/* Header */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span style={{ fontSize: 28, fontWeight: 700, color, fontFamily }}>{title}</span>
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: COLORS.surface,
              backgroundColor: color,
              padding: "4px 12px",
              borderRadius: 8,
              fontFamily: monoFamily,
              letterSpacing: "0.06em",
            }}
          >
            {role}
          </span>
        </div>
        <div style={{ fontSize: 14, color: COLORS.muted, fontFamily: monoFamily, marginTop: 4 }}>
          {subtitle}
        </div>
      </div>

      {/* GPU badge */}
      <div
        style={{
          backgroundColor: "#1a1a2e",
          borderRadius: 12,
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: 22, fontWeight: 700, color: "#76b900", fontFamily }}>
          {gpu}
        </span>
        <span style={{ fontSize: 14, color: "#76b900", fontFamily: monoFamily, opacity: 0.8 }}>
          {vram} VRAM
        </span>
      </div>

      {/* Specs */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {specs.map((s) => (
          <SpecRow key={s.label} label={s.label} value={s.value} color={color} />
        ))}
      </div>
    </div>
  );
};

export const InfraScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });
  const brevProgress = spring({ frame: frame - 8, fps, config: SPRING_SMOOTH });
  const arrowProgress = spring({ frame: frame - 80, fps, config: SPRING_SMOOTH });
  const footerProgress = spring({ frame: frame - 180, fps, config: SPRING_SMOOTH });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily,
        gap: 48,
      }}
    >
      {/* Title + BREV badge */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          opacity: titleProgress,
          transform: `translateY(${(1 - titleProgress) * 20}px)`,
        }}
      >
        <div style={{ fontSize: 56, fontWeight: 700, color: COLORS.white, letterSpacing: "-0.03em" }}>
          Compute Infrastructure
        </div>
        <div
          style={{
            opacity: brevProgress,
            display: "flex",
            alignItems: "center",
            gap: 10,
            backgroundColor: "#1a1a2e",
            borderRadius: 20,
            padding: "8px 20px",
            border: "1px solid #76b900",
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 700, color: "#76b900", fontFamily: monoFamily }}>
            NVIDIA
          </span>
          <span style={{ fontSize: 14, color: "#76b900", opacity: 0.6, fontFamily: monoFamily }}>
            /
          </span>
          <span style={{ fontSize: 14, fontWeight: 700, color: "#76b900", fontFamily: monoFamily }}>
            BREV
          </span>
        </div>
      </div>

      {/* Cluster cards + arrow */}
      <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
        <ClusterCard
          title="L40S"
          subtitle="NVIDIA Ada Lovelace"
          gpu="NVIDIA L40S"
          vram="48 GB"
          role="TRAIN"
          specs={[
            { label: "Framework", value: "Unsloth" },
            { label: "Method", value: "QLoRA 4-bit NF4" },
            { label: "Rank", value: "r=16, alpha=32" },
            { label: "Batch", value: "8 × grad_accum=4" },
            { label: "Duration", value: "~4 h / 2 epochs" },
          ]}
          color={COLORS.accent}
          delay={30}
        />

        {/* Arrow */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8,
            opacity: arrowProgress,
          }}
        >
          <div
            style={{
              fontSize: 13,
              color: COLORS.muted,
              fontFamily: monoFamily,
              letterSpacing: "0.04em",
            }}
          >
            adapter
          </div>
          <div style={{ fontSize: 36, color: COLORS.subtle }}>→</div>
          <div
            style={{
              fontSize: 13,
              color: COLORS.muted,
              fontFamily: monoFamily,
              letterSpacing: "0.04em",
            }}
          >
            HF Hub
          </div>
        </div>

        <ClusterCard
          title="L4"
          subtitle="NVIDIA Ada Lovelace"
          gpu="NVIDIA L4"
          vram="24 GB"
          role="SERVE"
          specs={[
            { label: "Engine", value: "vLLM" },
            { label: "Attention", value: "PagedAttention" },
            { label: "Decoding", value: "outlines (JSON)" },
            { label: "Latency p50", value: "~350 ms" },
            { label: "Throughput", value: "~8 req/s" },
          ]}
          color={COLORS.aligned}
          delay={60}
        />
      </div>

      {/* Footer note */}
      <div
        style={{
          opacity: footerProgress,
          fontSize: 16,
          color: COLORS.muted,
          fontFamily: monoFamily,
          letterSpacing: "0.04em",
          borderTop: `1px solid ${COLORS.border}`,
          paddingTop: 20,
          width: 940,
          textAlign: "center",
        }}
      >
        adapter weights pushed to HF Hub after training → pulled by vLLM at serve time
      </div>
    </AbsoluteFill>
  );
};
