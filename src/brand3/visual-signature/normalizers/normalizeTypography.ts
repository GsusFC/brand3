import type {
  NormalizedTypographySignals,
  TypographySignal,
  VisualAcquisitionResult,
  VisualSignalSource,
} from "../types";

const FONT_FAMILY = /font-family\s*:\s*([^;"'}]+)/gi;
const FONT_SIZE = /font-size\s*:\s*(\d+(?:\.\d+)?)px/gi;
const FONT_WEIGHT = /font-weight\s*:\s*(\d{3}|bold|normal|medium|semibold)/gi;
const HEADING_TAG = /<h([1-6])\b[^>]*>/gi;

export function normalizeTypography(acquisition: VisualAcquisitionResult): NormalizedTypographySignals {
  const html = [acquisition.renderedHtml ?? "", acquisition.rawHtml ?? ""].join("\n");
  const markdown = acquisition.markdown ?? "";
  const families = new Map<string, TypographySignal>();
  const sizeSamplesPx = collectNumberSamples(html, FONT_SIZE).slice(0, 24);
  const weights = collectWeightSamples(html);
  const headingLevels = collectHeadingLevels(html, markdown);

  for (const match of html.matchAll(FONT_FAMILY)) {
    for (const family of splitFamilies(match[1])) {
      const role = roleFromContext(html, match.index ?? 0);
      addFamily(families, family, role, "rendered_html");
    }
  }

  for (const item of inferMetadataFonts(acquisition.metadata)) {
    addFamily(families, item, "unknown", "metadata");
  }

  const fontFamilies = [...families.values()]
    .sort((left, right) => right.occurrences - left.occurrences)
    .slice(0, 12);
  const confidence = clamp(
    (fontFamilies.length ? 0.35 : 0) +
      (sizeSamplesPx.length ? 0.2 : 0) +
      (weights.length ? 0.15 : 0) +
      (headingLevels.length ? 0.2 : 0),
  );

  return {
    fontFamilies,
    headingScale: inferHeadingScale(sizeSamplesPx, headingLevels),
    weightRange: {
      min: weights.length ? Math.min(...weights) : undefined,
      max: weights.length ? Math.max(...weights) : undefined,
    },
    sizeSamplesPx,
    confidence,
  };
}

function addFamily(
  families: Map<string, TypographySignal>,
  family: string,
  role: TypographySignal["role"],
  source: VisualSignalSource,
): void {
  const normalized = normalizeFamily(family);
  if (!normalized) {
    return;
  }
  const existing = families.get(normalized.toLowerCase());
  if (existing) {
    existing.occurrences += 1;
    if (existing.role === "unknown" && role !== "unknown") {
      existing.role = role;
    }
    return;
  }
  families.set(normalized.toLowerCase(), {
    family: normalized,
    role,
    occurrences: 1,
    source,
    confidence: source === "metadata" ? 0.25 : 0.65,
  });
}

function splitFamilies(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim().replace(/^['"]|['"]$/g, ""))
    .filter((item) => item && !["inherit", "initial", "unset", "sans-serif", "serif", "monospace"].includes(item.toLowerCase()));
}

function normalizeFamily(value: string): string {
  return value.trim().replace(/\s+/g, " ").replace(/^var\(|\)$/g, "");
}

function collectNumberSamples(text: string, pattern: RegExp): number[] {
  return [...text.matchAll(pattern)]
    .map((match) => Number(match[1]))
    .filter((value) => Number.isFinite(value) && value >= 8 && value <= 160);
}

function collectWeightSamples(text: string): number[] {
  return [...text.matchAll(FONT_WEIGHT)]
    .map((match) => {
      const value = match[1].toLowerCase();
      if (value === "bold") return 700;
      if (value === "semibold") return 600;
      if (value === "medium") return 500;
      if (value === "normal") return 400;
      return Number(value);
    })
    .filter((value) => Number.isFinite(value) && value >= 100 && value <= 900);
}

function collectHeadingLevels(html: string, markdown: string): number[] {
  const htmlLevels = [...html.matchAll(HEADING_TAG)].map((match) => Number(match[1]));
  const markdownLevels = markdown
    .split("\n")
    .map((line) => line.match(/^(#{1,6})\s+/)?.[1].length)
    .filter((value): value is number => typeof value === "number");
  return [...htmlLevels, ...markdownLevels];
}

function roleFromContext(text: string, index: number): TypographySignal["role"] {
  const context = text.slice(Math.max(0, index - 160), index + 160).toLowerCase();
  if (/<h[1-6]\b/.test(context) || context.includes("display") || context.includes("hero")) {
    return "display";
  }
  if (context.includes("heading") || context.includes("headline") || context.includes("title")) {
    return "heading";
  }
  if (context.includes("button") || context.includes("nav") || context.includes("menu")) {
    return "ui";
  }
  if (context.includes("body") || context.includes("paragraph")) {
    return "body";
  }
  return "unknown";
}

function inferHeadingScale(
  sizeSamplesPx: number[],
  headingLevels: number[],
): NormalizedTypographySignals["headingScale"] {
  if (!sizeSamplesPx.length && !headingLevels.length) {
    return "unknown";
  }
  if (sizeSamplesPx.length >= 2) {
    const min = Math.min(...sizeSamplesPx);
    const max = Math.max(...sizeSamplesPx);
    const ratio = max / Math.max(1, min);
    if (ratio >= 3) return "expressive";
    if (ratio >= 1.8) return "moderate";
    return "flat";
  }
  return Math.min(...headingLevels) <= 1 && headingLevels.length >= 3 ? "moderate" : "flat";
}

function inferMetadataFonts(metadata: Record<string, unknown>): string[] {
  const raw = JSON.stringify(metadata);
  const matches = raw.match(/(?:font|typeface)[^"',:]*["':\s]+([A-Z][A-Za-z0-9\s-]{2,40})/g) ?? [];
  return matches.map((item) => item.split(/["':]/).pop() ?? "").filter(Boolean);
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
