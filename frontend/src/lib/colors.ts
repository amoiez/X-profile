// Validated dark-mode palette roles (from the dataviz reference palette).
// Categorical order is fixed and never cycled.

export const SERIES = ["#3987e5", "#199e70", "#c98500", "#9085e9"] as const;

export const SENTIMENT = {
  positive: "#199e70", // aqua/green
  neutral: "#6b7280", // muted gray
  negative: "#e66767", // red
} as const;

// Sequential single hue for magnitude (heatmap): light -> saturated blue.
export const HEAT_HUE = "#3987e5";

export function heatColor(intensity: number): string {
  // intensity in [0,1] -> alpha over the base surface.
  const a = 0.08 + Math.max(0, Math.min(1, intensity)) * 0.92;
  return `rgba(57, 135, 229, ${a.toFixed(3)})`;
}

// Automation score band -> status color (with label always shown alongside).
export function scoreColor(score: number): string {
  if (score >= 70) return "#e66767"; // high
  if (score >= 40) return "#c98500"; // moderate
  return "#199e70"; // low
}

export function scoreBand(score: number): string {
  if (score >= 70) return "High";
  if (score >= 40) return "Moderate";
  return "Low";
}

export const AXIS = "#6b7280";
export const GRID = "#243043";
export const SURFACE = "#111827";
