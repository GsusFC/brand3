import { FirecrawlVisualSignatureAdapter } from "./adapters/firecrawlAdapter";
import { normalizeAssetSignals } from "./normalizers/normalizeAssetSignals";
import { normalizeColors } from "./normalizers/normalizeColors";
import { normalizeComponentSignals } from "./normalizers/normalizeComponentSignals";
import { normalizeConsistencySignals } from "./normalizers/normalizeConsistencySignals";
import { normalizeLayoutSignals } from "./normalizers/normalizeLayoutSignals";
import { normalizeLogoSignals } from "./normalizers/normalizeLogoSignals";
import { normalizeTypography } from "./normalizers/normalizeTypography";
import { calculateExtractionConfidence } from "./scoring/calculateExtractionConfidence";
import type { VisualSignature, VisualSignatureInput, VisualSignatureOptions } from "./types";

export async function extractVisualSignature(
  input: VisualSignatureInput,
  options: VisualSignatureOptions = {},
): Promise<VisualSignature> {
  validateInput(input);
  const adapter = options.adapter ?? new FirecrawlVisualSignatureAdapter(options.firecrawl);
  const acquisition = await adapter.acquire(input);
  const colors = normalizeColors(acquisition);
  const typography = normalizeTypography(acquisition);
  const logo = normalizeLogoSignals(acquisition, input.brandName);
  const layout = normalizeLayoutSignals(acquisition);
  const components = normalizeComponentSignals(acquisition);
  const assets = normalizeAssetSignals(acquisition);
  const consistency = normalizeConsistencySignals({
    colors,
    typography,
    components,
    assets,
  });
  const extractionConfidence = calculateExtractionConfidence({
    acquisition,
    colors,
    typography,
    logo,
    layout,
    components,
    assets,
    consistency,
  });

  return {
    brandName: input.brandName,
    websiteUrl: input.websiteUrl,
    analyzedUrl: acquisition.finalUrl ?? acquisition.requestedUrl,
    acquisition: {
      adapter: acquisition.adapter,
      statusCode: acquisition.statusCode,
      acquiredAt: acquisition.acquiredAt,
      warnings: acquisition.warnings,
      errors: acquisition.errors,
    },
    colors,
    typography,
    logo,
    layout,
    components,
    assets,
    consistency,
    extractionConfidence,
    version: "visual-signature-mvp-1",
  };
}

function validateInput(input: VisualSignatureInput): void {
  if (!input.brandName?.trim()) {
    throw new Error("brandName is required");
  }
  if (!input.websiteUrl?.trim()) {
    throw new Error("websiteUrl is required");
  }
  try {
    const url = new URL(input.websiteUrl);
    if (!["http:", "https:"].includes(url.protocol)) {
      throw new Error("websiteUrl must use http or https");
    }
  } catch (error) {
    if (error instanceof Error && error.message === "websiteUrl must use http or https") {
      throw error;
    }
    throw new Error("websiteUrl must be a valid URL");
  }
}
