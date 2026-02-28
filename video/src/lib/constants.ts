// Design tokens from Redline design system
export const COLORS = {
  bg: "#0a0a0a",
  surface: "#141414",
  surfaceHover: "#1c1c1c",
  border: "#262626",

  // Semantic conflict colors (dark mode)
  contradicts: "#ef5350",
  fallsShort: "#ff9800",
  exceeds: "#fdd835",
  missing: "#ce93d8",
  aligned: "#81c784",

  // Status
  approved: "#81c784",
  flagged: "#ff9800",
  edited: "#64b5f6",
  pending: "#a1a1aa",

  // Core palette
  accent: "#ef5350",
  white: "#f5f5f5",
  muted: "#71717a",
  subtle: "#3f3f46",
} as const;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const TRANSITION_FRAMES = 15;

export const SCENE_DURATIONS = {
  title: 90,
  problem: 240,
  pipeline: 600,
  finetuning: 450,
  serving: 360,
  selfImprovement: 450,
  techStack: 240,
  closing: 150,
} as const;

export const TOTAL_FRAMES =
  Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0) -
  7 * TRANSITION_FRAMES;

export const SPRING_SMOOTH = { damping: 200 };
export const SPRING_SNAPPY = { damping: 20, stiffness: 200 };
export const SPRING_BOUNCY = { damping: 8 };
