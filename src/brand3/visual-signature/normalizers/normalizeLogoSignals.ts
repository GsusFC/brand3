import type {
  LogoCandidate,
  NormalizedLogoSignals,
  VisualAcquisitionResult,
  VisualAssetCandidate,
} from "../types";

export function normalizeLogoSignals(
  acquisition: VisualAcquisitionResult,
  brandName: string,
): NormalizedLogoSignals {
  const html = [acquisition.renderedHtml ?? "", acquisition.rawHtml ?? ""].join("\n");
  const candidates: LogoCandidate[] = [];
  const brandToken = normalizeToken(brandName);

  for (const image of acquisition.images) {
    const searchable = `${image.url} ${image.alt ?? ""}`.toLowerCase();
    if (image.roleHint === "logo" || searchable.includes("logo") || searchable.includes(brandToken)) {
      candidates.push(candidateFromAsset(image, locationFromContext(html, image.url)));
    }
  }

  for (const match of html.matchAll(/<img\b[^>]*(?:logo|brandmark|wordmark)[^>]*>/gi)) {
    candidates.push({
      url: attr(match[0], "src"),
      alt: attr(match[0], "alt"),
      location: locationFromContext(html, match[0], match.index ?? 0),
      source: "rendered_html",
      confidence: 0.72,
    });
  }

  const metadataIcon = metadataIconUrl(acquisition.metadata);
  if (metadataIcon) {
    candidates.push({
      url: metadataIcon,
      location: "metadata",
      source: "metadata",
      confidence: 0.45,
    });
  }

  const textualBrandMarkDetected = brandToken
    ? new RegExp(`<(?:a|span|div|strong)[^>]*>\\s*${escapeRegExp(brandName)}\\s*<`, "i").test(html)
    : false;
  if (textualBrandMarkDetected) {
    candidates.push({
      text: brandName,
      location: locationFromContext(html, brandName),
      source: "rendered_html",
      confidence: 0.55,
    });
  }

  const uniqueCandidates = dedupeCandidates(candidates).sort((left, right) => right.confidence - left.confidence);
  const primaryLocation = uniqueCandidates[0]?.location ?? "unknown";
  const faviconDetected = Boolean(metadataIcon || /rel=["'](?:shortcut )?icon["']/i.test(html));

  return {
    logoDetected: uniqueCandidates.some((item) => item.confidence >= 0.55),
    candidates: uniqueCandidates.slice(0, 8),
    faviconDetected,
    textualBrandMarkDetected,
    primaryLocation,
    confidence: clamp(
      (uniqueCandidates.length ? 0.35 : 0) +
        (uniqueCandidates.some((item) => item.location === "header" || item.location === "nav") ? 0.25 : 0) +
        (faviconDetected ? 0.15 : 0) +
        (textualBrandMarkDetected ? 0.15 : 0),
    ),
  };
}

function candidateFromAsset(asset: VisualAssetCandidate, location: LogoCandidate["location"]): LogoCandidate {
  return {
    url: asset.url,
    alt: asset.alt,
    location,
    source: asset.source,
    confidence: asset.roleHint === "logo" ? 0.78 : 0.55,
  };
}

function locationFromContext(html: string, needle: string, knownIndex?: number): LogoCandidate["location"] {
  const index = knownIndex ?? html.indexOf(needle);
  if (index < 0) {
    return "unknown";
  }
  const context = html.slice(Math.max(0, index - 1_000), index + 1_000).toLowerCase();
  if (context.includes("<header")) return "header";
  if (context.includes("<nav") || context.includes("navbar")) return "nav";
  if (context.includes("<footer")) return "footer";
  if (context.includes("<main")) return "body";
  return "unknown";
}

function attr(tag: string, name: string): string | undefined {
  const match = tag.match(new RegExp(`${name}\\s*=\\s*["']([^"']+)["']`, "i"));
  return match?.[1]?.trim();
}

function metadataIconUrl(metadata: Record<string, unknown>): string | undefined {
  for (const key of ["favicon", "faviconUrl", "icon", "ogImage", "image"]) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function dedupeCandidates(candidates: LogoCandidate[]): LogoCandidate[] {
  const seen = new Set<string>();
  const result: LogoCandidate[] = [];
  for (const candidate of candidates) {
    const key = candidate.url ?? candidate.text ?? candidate.alt ?? "";
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(candidate);
  }
  return result;
}

function normalizeToken(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
