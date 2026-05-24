import type { ComponentSignal, NormalizedComponentSignals, VisualAcquisitionResult } from "../types";

export function normalizeComponentSignals(acquisition: VisualAcquisitionResult): NormalizedComponentSignals {
  const html = [acquisition.renderedHtml ?? "", acquisition.rawHtml ?? ""].join("\n");
  const markdown = acquisition.markdown ?? "";
  const components: ComponentSignal[] = [
    signal("navigation", count(html, /<nav\b/gi), navLabels(html), "rendered_html", 0.7),
    signal("button", count(html, /<button\b/gi), buttonLabels(html), "rendered_html", 0.72),
    signal("cta", ctaLabels(html, markdown).length, ctaLabels(html, markdown), "rendered_html", 0.62),
    signal("form", count(html, /<form\b|<input\b|<textarea\b|<select\b/gi), [], "rendered_html", 0.68),
    signal("card", count(html, /\bcard\b|<article\b/gi), [], "rendered_html", 0.48),
    signal("accordion", count(html, /\baccordion\b|aria-expanded=/gi), [], "rendered_html", 0.45),
    signal("tabs", count(html, /\btablist\b|\btabs?\b|role=["']tab/gi), [], "rendered_html", 0.45),
    signal("modal", count(html, /\bmodal\b|role=["']dialog/gi), [], "rendered_html", 0.45),
    signal("pricing", count(html, /\bpricing\b|\bprice-card\b|\bplan\b/gi), [], "rendered_html", 0.42),
  ].filter((item) => item.count > 0);

  const primaryCtas = ctaLabels(html, markdown).slice(0, 8);
  const interactionPatterns = new Set<NormalizedComponentSignals["interactionPatterns"][number]>();
  for (const item of components) {
    if (item.type === "form") interactionPatterns.add("form");
    if (item.type === "navigation") interactionPatterns.add("navigation");
    if (item.type === "accordion") interactionPatterns.add("accordion");
    if (item.type === "tabs") interactionPatterns.add("tabs");
    if (item.type === "modal") interactionPatterns.add("modal");
  }

  return {
    components,
    primaryCtas,
    interactionPatterns: interactionPatterns.size ? [...interactionPatterns] : ["unknown"],
    confidence: clamp(
      (html.trim() ? 0.25 : 0) +
        Math.min(0.35, components.length * 0.06) +
        (primaryCtas.length ? 0.15 : 0) +
        (interactionPatterns.size ? 0.15 : 0),
    ),
  };
}

function signal(
  type: ComponentSignal["type"],
  countValue: number,
  labels: string[],
  source: ComponentSignal["source"],
  confidence: number,
): ComponentSignal {
  return {
    type,
    count: countValue,
    labels: unique(labels).slice(0, 10),
    source,
    confidence,
  };
}

function buttonLabels(html: string): string[] {
  return [...html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/gi)]
    .map((match) => cleanText(match[1]))
    .filter(Boolean);
}

function navLabels(html: string): string[] {
  return [...html.matchAll(/<nav\b[^>]*>([\s\S]*?)<\/nav>/gi)]
    .flatMap((match) => [...match[1].matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)].map((link) => cleanText(link[1])))
    .filter(Boolean);
}

function ctaLabels(html: string, markdown: string): string[] {
  const htmlLabels = [...html.matchAll(/<(?:a|button)\b[^>]*(?:btn|button|cta|primary|signup|demo|get-started)[^>]*>([\s\S]*?)<\/(?:a|button)>/gi)]
    .map((match) => cleanText(match[1]))
    .filter(Boolean);
  const markdownLabels = [...markdown.matchAll(/\[([^\]]{2,80})\]\([^)]+\)/g)]
    .map((match) => match[1].trim())
    .filter((label) => /get|start|try|book|demo|contact|sign|join|buy|pricing|learn/i.test(label));
  return unique([...htmlLabels, ...markdownLabels]);
}

function cleanText(value: string): string {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 80);
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function count(value: string, pattern: RegExp): number {
  return [...value.matchAll(pattern)].length;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
