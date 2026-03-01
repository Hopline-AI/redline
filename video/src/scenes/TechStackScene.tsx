import React from "react";
import {
  AbsoluteFill,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { COLORS, SPRING_SNAPPY, SPRING_SMOOTH } from "../lib/constants";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

const TECHS = [
  { name: "Mistral", color: COLORS.accent },
  { name: "NVIDIA BREV", color: "#76b900" },
  { name: "W&B", color: COLORS.exceeds },
  { name: "Hugging Face", color: COLORS.flagged },
  { name: "vLLM", color: COLORS.edited },
  { name: "FastAPI", color: COLORS.aligned },
  { name: "Unsloth", color: "#a78bfa" },
];

export const TechStackScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });
  const tagProgress = spring({ frame: frame - 100, fps, config: SPRING_SMOOTH });

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
        Built With
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 20,
          maxWidth: 1100,
        }}
      >
        {TECHS.map((tech, i) => {
          const progress = spring({
            frame: frame - (12 + i * 8),
            fps,
            config: SPRING_SNAPPY,
          });

          return (
            <div
              key={tech.name}
              style={{
                padding: "24px 44px",
                borderRadius: 16,
                backgroundColor: COLORS.surface,
                border: `2px solid ${tech.color}`,
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                opacity: progress,
                transform: `scale(${0.8 + 0.2 * progress})`,
              }}
            >
              <span style={{ fontSize: 28, fontWeight: 700, color: tech.color }}>
                {tech.name}
              </span>
            </div>
          );
        })}
      </div>

      <div
        style={{
          fontSize: 20,
          color: COLORS.muted,
          opacity: tagProgress,
          letterSpacing: "0.04em",
        }}
      >
        Mistral Worldwide Hackathon 2026
      </div>
    </AbsoluteFill>
  );
};
