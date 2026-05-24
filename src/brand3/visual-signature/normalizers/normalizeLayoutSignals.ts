import type { NormalizedLayoutSignals, VisualAcquisitionResult } from "../types";

export function normalizeLayoutSignals(acquisition: VisualAcquisitionResult): NormalizedLayoutSignals {
  const html = [acquisition.renderedHtml ?? "", acquisition.rawHtml ?? ""].join("\n");
  const lower = html.toLowerCase();
  const sectionCount = count(lower, /<section\b/g) + count(lower, /class=["'][^"']*\bsection\b/gi);
  const layoutPatterns = new Set<NormalizedLayoutSignals["layoutPatterns"][number]>();

  if (/\bgrid\b|display\s*:\s*grid|grid-template/i.test(html)) {
    layoutPatterns.add("grid");
  }
  if (/\bflex\b|display\s*:\s*flex/i.test(html)) {
    layoutPatterns.add("flex");
  }
  if (/\bcol-|columns?|two-column|three-column|split\b/i.test(html)) {
    layoutPatterns.add("multi_column");
  }
  if (!layoutPatterns.size && html.trim()) {
    layoutPatterns.add("single_column");
  }
  if (/position\s*:\s*sticky|sticky|fixed top|navbar-fixed/i.test(html)) {
    layoutPatterns.add("sticky_nav");
  }

  return {
    hasHeader: lower.includes("<header") || /\bheader\b/.test(lower),
    hasNavigation: lower.includes("<nav") || /\bnavbar\b|\bmenu\b/.test(lower),
    hasHero: /\bhero\b|above[-_\s]?the[-_\s]?fold|<h1\b/i.test(html),
    hasMainContent: lower.includes("<main") || lower.length > 1_000,
    hasFooter: lower.includes("<footer") || /\bfooter\b/.test(lower),
    sectionCount,
    layoutPatterns: layoutPatterns.size ? [...layoutPatterns] : ["unknown"],
    visualDensity: inferDensity(html, sectionCount),
    confidence: clamp(
      (html.trim() ? 0.3 : 0) +
        (lower.includes("<main") ? 0.15 : 0) +
        (lower.includes("<header") || lower.includes("<nav") ? 0.2 : 0) +
        (sectionCount ? 0.15 : 0) +
        (layoutPatterns.size ? 0.15 : 0),
    ),
  };
}

function inferDensity(
  html: string,
  sectionCount: number,
): NormalizedLayoutSignals["visualDensity"] {
  if (!html.trim()) {
    return "unknown";
  }
  const textLength = stripTags(html).replace(/\s+/g, " ").trim().length;
  const interactiveCount = count(html, /<(?:a|button|input|select|textarea)\b/gi);
  const denominator = Math.max(1, sectionCount || count(html, /<div\b/gi) / 8);
  const density = (textLength / 500 + interactiveCount / 8) / denominator;
  if (density < 1.1) return "sparse";
  if (density > 3.2) return "dense";
  return "balanced";
}

function stripTags(value: string): string {
  return value.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, "").replace(/<[^>]+>/g, " ");
}

function count(value: string, pattern: RegExp): number {
  return [...value.matchAll(pattern)].length;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
