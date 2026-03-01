// Design tokens from Redline design system (light theme from colors.json)
export const COLORS = {
  bg: "#F5F0E8",
  surface: "#1a1a2e",
  surfaceHover: "#24243c",
  border: "#d4cfc4",

  // Semantic conflict colors (light theme)
  contradicts: "#d32f2f",
  fallsShort: "#e65100",
  exceeds: "#f9a825",
  missing: "#7b1fa2",
  aligned: "#2e7d32",

  // Status (light theme)
  approved: "#2e7d32",
  flagged: "#e65100",
  edited: "#1565c0",
  pending: "#71717a",

  // Core palette
  accent: "#d32f2f",
  white: "#1a1a1a",
  muted: "#6b6b6b",
  subtle: "#c4bfb4",
} as const;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const TRANSITION_FRAMES = 15;

export const SCENE_DURATIONS = {
  title: 90,
  problem: 240,
  pipeline: 360,
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
