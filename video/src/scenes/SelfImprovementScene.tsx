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

// Each node in the MCP loop cycle
const LOOP_NODES: {
  label: string;
  tool: string;
  detail: string;
  color: string;
}[] = [
  {
    label: "Inspect",
    tool: "query_wandb_tool",
    detail: "fetch latest eval run",
    color: COLORS.edited,
  },
  {
    label: "Diagnose",
    tool: "query_weave_traces_tool",
    detail: "find weak category",
    color: COLORS.exceeds,
  },
  {
    label: "Generate",
    tool: "generate_targeted_data.py",
    detail: "synthetic training pairs",
    color: COLORS.accent,
  },
  {
    label: "Retrain",
    tool: "BREV L40S",
    detail: "Unsloth QLoRA fine-tune",
    color: "#76b900",
  },
  {
    label: "Evaluate",
    tool: "finetuned_eval.py",
    detail: "6 scorers via Weave",
    color: COLORS.aligned,
  },
  {
    label: "Report",
    tool: "create_wandb_report_tool",
    detail: "publish delta to W&B",
    color: COLORS.muted,
  },
];

const NODE_DELAY = 28;
const START_AT = 18;

// Positions around an ellipse (right-side open, clockwise from top)
function ellipsePos(
  i: number,
  total: number,
  cx: number,
  cy: number,
  rx: number,
  ry: number,
): { x: number; y: number } {
  // Distribute from ~-90deg clockwise, skip the right-side opening
  const startAngle = -Math.PI / 2;
  const sweep = (2 * Math.PI * 5) / 6; // 5/6 of full circle, leaves right side open
  const angle = startAngle + (i / (total - 1)) * sweep;
  return {
    x: cx + rx * Math.cos(angle),
    y: cy + ry * Math.sin(angle),
  };
}

const LoopNode: React.FC<{
  node: (typeof LOOP_NODES)[0];
  x: number;
  y: number;
  delay: number;
}> = ({ node, x, y, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({ frame: frame - delay, fps, config: SPRING_SNAPPY });

  return (
    <div
      style={{
        position: "absolute",
        left: x - 130,
        top: y - 52,
        width: 260,
        opacity: progress,
        transform: `scale(${0.85 + 0.15 * progress})`,
      }}
    >
      <div
        style={{
          backgroundColor: COLORS.surface,
          borderRadius: 14,
          border: `1px solid ${COLORS.border}`,
          borderLeftWidth: 4,
          borderLeftColor: node.color,
          padding: "14px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 6,
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        }}
      >
        <span style={{ fontSize: 18, fontWeight: 700, color: node.color, fontFamily }}>
          {node.label}
        </span>
        <span
          style={{
            fontSize: 13,
            color: COLORS.white,
            fontFamily: monoFamily,
            backgroundColor: COLORS.bg,
            padding: "3px 8px",
            borderRadius: 6,
            display: "inline-block",
          }}
        >
          {node.tool}
        </span>
        <span style={{ fontSize: 12, color: COLORS.muted, fontFamily }}>
          {node.detail}
        </span>
      </div>
    </div>
  );
};

export const SelfImprovementScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  // Accuracy delta counter
  const accDelay = START_AT + LOOP_NODES.length * NODE_DELAY + 30;
  const accProgress = spring({
    frame: frame - accDelay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 120,
  });
  const accuracy = interpolate(accProgress, [0, 1], [84.8, 94.0]);

  // Center of the ellipse layout
  const cx = 960;
  const cy = 560;
  const rx = 400;
  const ry = 270;

  // Arrow ring opacity — fades in after all nodes appear
  const ringDelay = START_AT + LOOP_NODES.length * NODE_DELAY;
  const ringOpacity = interpolate(frame, [ringDelay, ringDelay + 20], [0, 0.25], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, fontFamily }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 44,
          width: "100%",
          textAlign: "center",
          fontSize: 52,
          fontWeight: 700,
          color: COLORS.white,
          opacity: titleProgress,
          transform: `translateY(${(1 - titleProgress) * 20}px)`,
          letterSpacing: "-0.03em",
        }}
      >
        W&B MCP Self-Improvement Loop
      </div>

      {/* Subtitle badges */}
      <div
        style={{
          position: "absolute",
          top: 116,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          gap: 16,
          opacity: titleProgress,
        }}
      >
        {["Claude Code", "W&B MCP Server", "BREV L40S"].map((label) => (
          <span
            key={label}
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: COLORS.accent,
              padding: "5px 16px",
              borderRadius: 20,
              border: `1.5px solid ${COLORS.accent}`,
              backgroundColor: COLORS.surface,
              fontFamily: monoFamily,
              letterSpacing: "0.04em",
            }}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Ellipse guide ring (SVG, subtle) */}
      <svg
        style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%" }}
        viewBox="0 0 1920 1080"
      >
        <ellipse
          cx={cx}
          cy={cy}
          rx={rx + 10}
          ry={ry + 10}
          fill="none"
          stroke={COLORS.subtle}
          strokeWidth={1.5}
          strokeDasharray="8 6"
          opacity={ringOpacity}
        />
        {/* Clockwise arrow hint at the bottom-right gap */}
        <path
          d={`M ${cx + rx + 10},${cy + 30} Q ${cx + rx + 40},${cy} ${cx + rx + 10},${cy - 30}`}
          fill="none"
          stroke={COLORS.subtle}
          strokeWidth={2}
          markerEnd="none"
          opacity={ringOpacity}
        />
        <text
          x={cx + rx + 20}
          y={cy + 6}
          fontSize={18}
          fill={COLORS.subtle}
          opacity={ringOpacity}
          fontFamily={monoFamily}
        >
          ↻
        </text>
      </svg>

      {/* Loop nodes */}
      {LOOP_NODES.map((node, i) => {
        const { x, y } = ellipsePos(i, LOOP_NODES.length, cx, cy, rx, ry);
        return (
          <LoopNode
            key={node.label}
            node={node}
            x={x}
            y={y}
            delay={START_AT + i * NODE_DELAY}
          />
        );
      })}

      {/* Centre: accuracy delta readout */}
      <div
        style={{
          position: "absolute",
          left: cx - 130,
          top: cy - 80,
          width: 260,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          opacity: accProgress,
        }}
      >
        <span
          style={{ fontSize: 13, color: COLORS.muted, fontFamily: monoFamily, letterSpacing: "0.06em" }}
        >
          per-type accuracy
        </span>
        <span
          style={{
            fontSize: 72,
            fontWeight: 700,
            color: COLORS.aligned,
            fontFamily: monoFamily,
            lineHeight: 1,
          }}
        >
          {accuracy.toFixed(1)}%
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              fontSize: 15,
              color: COLORS.muted,
              fontFamily: monoFamily,
              textDecoration: "line-through",
            }}
          >
            84.8%
          </span>
          <span style={{ fontSize: 20, color: COLORS.aligned }}>→</span>
          <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.aligned, fontFamily: monoFamily }}>
            94.0%
          </span>
        </div>
        <span
          style={{
            fontSize: 12,
            color: COLORS.muted,
            fontFamily: monoFamily,
            marginTop: 4,
            padding: "3px 10px",
            borderRadius: 8,
            border: `1px solid ${COLORS.border}`,
          }}
        >
          +1 MCP cycle
        </span>
      </div>
    </AbsoluteFill>
  );
};
