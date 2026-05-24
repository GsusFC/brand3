import type {
  ColorSignal,
  NormalizedColorSignals,
  VisualAcquisitionResult,
  VisualSignalSource,
} from "../types";

const HEX_COLOR = /#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g;
const RGB_COLOR = /rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})(?:[\s,/]+[\d.]+)?\s*\)/gi;

export function normalizeColors(acquisition: VisualAcquisitionResult): NormalizedColorSignals {
  const textSources: Array<{ text: string; source: VisualSignalSource }> = [
    { text: acquisition.renderedHtml ?? "", source: "rendered_html" },
    { text: acquisition.rawHtml ?? "", source: "raw_html" },
    { text: acquisition.markdown ?? "", source: "markdown" },
  ];
  const counts = new Map<string, ColorSignal>();

  for (const item of textSources) {
    collectHexColors(item.text, item.source, counts);
    collectRgbColors(item.text, item.source, counts);
  }

  const palette = [...counts.values()]
    .sort((left, right) => right.occurrences - left.occurrences)
    .slice(0, 24)
    .map((item) => ({
      ...item,
      confidence: clamp(item.confidence + Math.min(0.25, item.occurrences * 0.02)),
    }));

  const dominantColors = palette.slice(0, 8).map((item) => item.hex);
  const accentCandidates = palette
    .filter((item) => item.role === "accent" || saturation(item.hex) > 0.35)
    .slice(0, 6)
    .map((item) => item.hex);
  const backgroundCandidates = palette
    .filter((item) => item.role === "background" || luminance(item.hex) > 0.82 || luminance(item.hex) < 0.12)
    .slice(0, 6)
    .map((item) => item.hex);
  const textColorCandidates = palette
    .filter((item) => item.role === "text" || luminance(item.hex) < 0.2)
    .slice(0, 6)
    .map((item) => item.hex);

  return {
    palette,
    dominantColors,
    accentCandidates,
    backgroundCandidates,
    textColorCandidates,
    paletteComplexity: complexity(palette.length),
    confidence: palette.length ? clamp(0.35 + Math.min(0.55, palette.length / 18)) : 0.05,
  };
}

function collectHexColors(
  text: string,
  source: VisualSignalSource,
  counts: Map<string, ColorSignal>,
): void {
  for (const match of text.matchAll(HEX_COLOR)) {
    const hex = normalizeHex(match[0]);
    if (!hex) {
      continue;
    }
    addColor(counts, hex, roleFromContext(text, match.index ?? 0), source);
  }
}

function collectRgbColors(
  text: string,
  source: VisualSignalSource,
  counts: Map<string, ColorSignal>,
): void {
  for (const match of text.matchAll(RGB_COLOR)) {
    const red = clampChannel(Number(match[1]));
    const green = clampChannel(Number(match[2]));
    const blue = clampChannel(Number(match[3]));
    const hex = rgbToHex(red, green, blue);
    addColor(counts, hex, roleFromContext(text, match.index ?? 0), source);
  }
}

function addColor(
  counts: Map<string, ColorSignal>,
  hex: string,
  role: ColorSignal["role"],
  source: VisualSignalSource,
): void {
  const existing = counts.get(hex);
  if (existing) {
    existing.occurrences += 1;
    if (existing.role === "unknown" && role !== "unknown") {
      existing.role = role;
    }
    return;
  }
  counts.set(hex, {
    hex,
    role,
    occurrences: 1,
    source,
    confidence: source === "rendered_html" || source === "raw_html" ? 0.6 : 0.35,
  });
}

function roleFromContext(text: string, index: number): ColorSignal["role"] {
  const context = text.slice(Math.max(0, index - 80), index + 80).toLowerCase();
  if (context.includes("background") || context.includes("bg-")) {
    return "background";
  }
  if (context.includes("color:") || context.includes("text-") || context.includes("foreground")) {
    return "text";
  }
  if (context.includes("border") || context.includes("outline")) {
    return "border";
  }
  if (context.includes("accent") || context.includes("primary") || context.includes("cta")) {
    return "accent";
  }
  if (context.includes("surface") || context.includes("card")) {
    return "surface";
  }
  return "unknown";
}

function normalizeHex(value: string): string | null {
  const raw = value.replace("#", "").toLowerCase();
  if (raw.length === 3 || raw.length === 4) {
    return `#${raw[0]}${raw[0]}${raw[1]}${raw[1]}${raw[2]}${raw[2]}`;
  }
  if (raw.length === 6 || raw.length === 8) {
    return `#${raw.slice(0, 6)}`;
  }
  return null;
}

function rgbToHex(red: number, green: number, blue: number): string {
  return `#${[red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function clampChannel(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value || 0)));
}

function complexity(count: number): NormalizedColorSignals["paletteComplexity"] {
  if (count <= 0) {
    return "unknown";
  }
  if (count <= 5) {
    return "low";
  }
  if (count <= 14) {
    return "medium";
  }
  return "high";
}

function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.03928
      ? normalized / 12.92
      : Math.pow((normalized + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function saturation(hex: string): number {
  const [r, g, b] = rgb(hex).map((channel) => channel / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  return max === 0 ? 0 : (max - min) / max;
}

function rgb(hex: string): [number, number, number] {
  const raw = hex.replace("#", "");
  return [
    Number.parseInt(raw.slice(0, 2), 16),
    Number.parseInt(raw.slice(2, 4), 16),
    Number.parseInt(raw.slice(4, 6), 16),
  ];
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
