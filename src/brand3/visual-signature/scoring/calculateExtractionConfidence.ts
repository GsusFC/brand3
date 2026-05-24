import type {
  ExtractionConfidence,
  NormalizedAssetSignals,
  NormalizedColorSignals,
  NormalizedComponentSignals,
  NormalizedConsistencySignals,
  NormalizedLayoutSignals,
  NormalizedLogoSignals,
  NormalizedTypographySignals,
  VisualAcquisitionResult,
} from "../types";

export function calculateExtractionConfidence(input: {
  acquisition: VisualAcquisitionResult;
  colors: NormalizedColorSignals;
  typography: NormalizedTypographySignals;
  logo: NormalizedLogoSignals;
  layout: NormalizedLayoutSignals;
  components: NormalizedComponentSignals;
  assets: NormalizedAssetSignals;
  consistency: NormalizedConsistencySignals;
}): ExtractionConfidence {
  const acquisitionScore = scoreAcquisition(input.acquisition);
  const htmlCoverage = scoreHtmlCoverage(input.acquisition);
  const signalCoverage = average([
    input.colors.confidence,
    input.typography.confidence,
    input.logo.confidence,
    input.layout.confidence,
    input.components.confidence,
    input.assets.confidence,
  ]);
  const consistencyCoverage = input.consistency.confidence;
  const score = round(
    acquisitionScore * 0.25 +
      htmlCoverage * 0.25 +
      signalCoverage * 0.35 +
      consistencyCoverage * 0.15,
  );
  const limitations = limitationsFor(input.acquisition, {
    htmlCoverage,
    signalCoverage,
    consistencyCoverage,
  });

  return {
    score,
    level: score >= 0.75 ? "high" : score >= 0.45 ? "medium" : "low",
    factors: {
      acquisition: acquisitionScore,
      htmlCoverage,
      signalCoverage,
      consistencyCoverage,
    },
    limitations,
  };
}

function scoreAcquisition(acquisition: VisualAcquisitionResult): number {
  if (acquisition.errors.length) {
    return 0.1;
  }
  const status = acquisition.statusCode ?? 0;
  if (status >= 200 && status < 300) {
    return 0.9;
  }
  if (status >= 300 && status < 400) {
    return 0.75;
  }
  return 0.45;
}

function scoreHtmlCoverage(acquisition: VisualAcquisitionResult): number {
  const rendered = acquisition.renderedHtml?.length ?? 0;
  const raw = acquisition.rawHtml?.length ?? 0;
  const markdown = acquisition.markdown?.length ?? 0;
  const total = rendered + raw * 0.7 + markdown * 0.35;
  if (total > 20_000) return 0.9;
  if (total > 5_000) return 0.72;
  if (total > 1_000) return 0.5;
  if (total > 0) return 0.25;
  return 0;
}

function limitationsFor(
  acquisition: VisualAcquisitionResult,
  scores: { htmlCoverage: number; signalCoverage: number; consistencyCoverage: number },
): string[] {
  const limitations: string[] = [];
  if (acquisition.errors.length) {
    limitations.push("acquisition_errors_present");
  }
  if (!acquisition.screenshot?.url) {
    limitations.push("screenshot_not_available");
  }
  if (scores.htmlCoverage < 0.5) {
    limitations.push("html_coverage_limited");
  }
  if (scores.signalCoverage < 0.45) {
    limitations.push("visual_signal_coverage_limited");
  }
  if (scores.consistencyCoverage < 0.45) {
    limitations.push("consistency_inference_limited");
  }
  return limitations;
}

function average(values: number[]): number {
  if (!values.length) {
    return 0;
  }
  return round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function round(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
