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

const BEFORE_COST = 18000;
const AFTER_COST = 2500;
const SAVINGS = BEFORE_COST - AFTER_COST;
const ANNUAL = SAVINGS * 12;

const BREAKDOWN = [
  { label: "Lawyer rate (CA avg)", before: "$400/hr", after: "Spot-check only" },
  { label: "Hours per policy", before: "40-80 hrs", after: "4-6 hrs" },
  { label: "Review cycle", before: "2-4 weeks", after: "Under 1 hour" },
  { label: "Consistency", before: "Varies by lawyer", after: "Deterministic" },
];

export const SavingsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: SPRING_SMOOTH });

  // Bar animations
  const barDelay = 21;
  const beforeBarProgress = spring({
    frame: frame - barDelay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 50,
  });
  const afterBarProgress = spring({
    frame: frame - barDelay - 31,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 50,
  });

  // Savings counter
  const counterDelay = 111;
  const counterProgress = spring({
    frame: frame - counterDelay,
    fps,
    config: SPRING_SMOOTH,
    durationInFrames: 80,
  });
  const savingsCount = Math.round(SAVINGS * counterProgress);
  const annualCount = Math.round(ANNUAL * counterProgress);

  // Breakdown rows
  const breakdownDelay = 171;

  // Max bar height
  const maxBarH = 320;
  const beforeH = maxBarH;
  const afterH = maxBarH * (AFTER_COST / BEFORE_COST);

  // Percentage badge
  const pctDelay = 151;
  const pctProgress = spring({
    frame: frame - pctDelay,
    fps,
    config: SPRING_SNAPPY,
  });
  const pctValue = Math.round(
    interpolate(counterProgress, [0, 1], [0, 86]),
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        fontFamily,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 40,
      }}
    >
      {/* Title */}
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
        The Business Case
      </div>

      <div style={{ display: "flex", gap: 80, alignItems: "flex-end" }}>
        {/* Left: Bar chart comparison */}
        <div style={{ display: "flex", gap: 40, alignItems: "flex-end" }}>
          {/* Before bar */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.accent,
                fontFamily: monoFamily,
                opacity: beforeBarProgress,
              }}
            >
              ${BEFORE_COST.toLocaleString()}
            </span>
            <div
              style={{
                width: 100,
                height: beforeH * beforeBarProgress,
                backgroundColor: COLORS.accent,
                borderRadius: "8px 8px 0 0",
                opacity: 0.85,
              }}
            />
            <span style={{ fontSize: 16, color: COLORS.muted, fontWeight: 700 }}>
              Before
            </span>
          </div>

          {/* After bar */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.aligned,
                fontFamily: monoFamily,
                opacity: afterBarProgress,
              }}
            >
              ${AFTER_COST.toLocaleString()}
            </span>
            <div
              style={{
                width: 100,
                height: afterH * afterBarProgress,
                backgroundColor: COLORS.aligned,
                borderRadius: "8px 8px 0 0",
              }}
            />
            <span style={{ fontSize: 16, color: COLORS.muted, fontWeight: 700 }}>
              After
            </span>
          </div>

          {/* per month label */}
          <div
            style={{
              position: "absolute",
              left: 210,
              bottom: 235,
              fontSize: 14,
              color: COLORS.muted,
              opacity: beforeBarProgress,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            monthly compliance cost
          </div>
        </div>

        {/* Right: Savings + Breakdown */}
        <div style={{ display: "flex", flexDirection: "column", gap: 28, width: 600 }}>
          {/* Big savings number */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span
              style={{
                fontSize: 14,
                color: COLORS.muted,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                opacity: counterProgress,
              }}
            >
              Monthly savings
            </span>
            <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
              <span
                style={{
                  fontSize: 72,
                  fontWeight: 700,
                  color: COLORS.aligned,
                  fontFamily: monoFamily,
                  lineHeight: 1,
                  opacity: counterProgress,
                }}
              >
                ${savingsCount.toLocaleString()}
              </span>
              <span
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: COLORS.accent,
                  opacity: pctProgress,
                  transform: `scale(${0.8 + 0.2 * pctProgress})`,
                  padding: "4px 16px",
                  borderRadius: 8,
                  backgroundColor: `${COLORS.accent}12`,
                  border: `2px solid ${COLORS.accent}`,
                }}
              >
                -{pctValue}%
              </span>
            </div>
            <span
              style={{
                fontSize: 18,
                color: COLORS.muted,
                fontFamily: monoFamily,
                opacity: counterProgress,
                marginTop: 4,
              }}
            >
              ${annualCount.toLocaleString()}/year
            </span>
          </div>

          {/* Breakdown table */}
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {BREAKDOWN.map((row, i) => {
              const rowProgress = spring({
                frame: frame - (breakdownDelay + i * 20),
                fps,
                config: SPRING_SNAPPY,
              });

              return (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "14px 20px",
                    opacity: rowProgress,
                    transform: `translateX(${(1 - rowProgress) * 30}px)`,
                    borderBottom: i < BREAKDOWN.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  }}
                >
                  <span style={{ fontSize: 16, color: COLORS.muted, width: 200 }}>
                    {row.label}
                  </span>
                  <span
                    style={{
                      fontSize: 16,
                      color: COLORS.accent,
                      width: 180,
                      fontFamily: monoFamily,
                      textDecoration: "line-through",
                      opacity: 0.6,
                    }}
                  >
                    {row.before}
                  </span>
                  <span
                    style={{
                      fontSize: 16,
                      fontWeight: 700,
                      color: COLORS.aligned,
                      fontFamily: monoFamily,
                    }}
                  >
                    {row.after}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Source line */}
          <span
            style={{
              fontSize: 13,
              color: COLORS.subtle,
              opacity: counterProgress,
              fontStyle: "italic",
            }}
          >
            Based on CA employment law compliance costs (ACC, Thomson Reuters 2025)
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
