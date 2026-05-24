import type { NormalizedAssetSignals, VisualAcquisitionResult, VisualAssetCandidate } from "../types";

export function normalizeAssetSignals(acquisition: VisualAcquisitionResult): NormalizedAssetSignals {
  const html = [acquisition.renderedHtml ?? "", acquisition.rawHtml ?? ""].join("\n");
  const images = acquisition.images;
  const logoImageCandidates = images.filter((item) => item.roleHint === "logo" || textFor(item).includes("logo"));
  const iconCandidates = images.filter((item) => item.roleHint === "icon" || textFor(item).includes("icon"));
  const svgCount = count(html, /<svg\b|\.svg\b/gi);
  const videoCount = count(html, /<video\b|youtube\.com|vimeo\.com|\.mp4\b/gi);
  const backgroundImageCount = count(html, /background(?:-image)?\s*:\s*url\(/gi);
  const assetMix = new Set<NormalizedAssetSignals["assetMix"][number]>();

  if (logoImageCandidates.length) assetMix.add("logo");
  if (iconCandidates.length || svgCount) assetMix.add("icon");
  if (images.some((item) => textFor(item).includes("illustration") || textFor(item).includes("graphic"))) {
    assetMix.add("illustration");
  }
  if (images.some((item) => item.roleHint === "photo" || /\.(?:jpg|jpeg|webp|png)(?:\?|$)/i.test(item.url))) {
    assetMix.add("photo");
  }
  if (videoCount) assetMix.add("video");
  if (acquisition.screenshot?.url) assetMix.add("screenshot");

  return {
    imageCount: images.length,
    svgCount,
    videoCount,
    backgroundImageCount,
    logoImageCandidates: logoImageCandidates.slice(0, 8),
    iconCandidates: iconCandidates.slice(0, 12),
    screenshotAvailable: Boolean(acquisition.screenshot?.url),
    assetMix: assetMix.size ? [...assetMix] : ["unknown"],
    confidence: clamp(
      (images.length ? 0.25 : 0) +
        (svgCount ? 0.1 : 0) +
        (acquisition.screenshot?.url ? 0.25 : 0) +
        (html.trim() ? 0.2 : 0) +
        Math.min(0.15, assetMix.size * 0.04),
    ),
  };
}

function textFor(item: VisualAssetCandidate): string {
  return `${item.url} ${item.alt ?? ""}`.toLowerCase();
}

function count(value: string, pattern: RegExp): number {
  return [...value.matchAll(pattern)].length;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
