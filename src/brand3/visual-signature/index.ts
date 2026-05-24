export { extractVisualSignature } from "./extractVisualSignature";
export { FirecrawlVisualSignatureAdapter } from "./adapters/firecrawlAdapter";
export { normalizeAssetSignals } from "./normalizers/normalizeAssetSignals";
export { normalizeColors } from "./normalizers/normalizeColors";
export { normalizeComponentSignals } from "./normalizers/normalizeComponentSignals";
export { normalizeConsistencySignals } from "./normalizers/normalizeConsistencySignals";
export { normalizeLayoutSignals } from "./normalizers/normalizeLayoutSignals";
export { normalizeLogoSignals } from "./normalizers/normalizeLogoSignals";
export { normalizeTypography } from "./normalizers/normalizeTypography";
export { calculateExtractionConfidence } from "./scoring/calculateExtractionConfidence";
export type {
  ColorSignal,
  ComponentSignal,
  ExtractionConfidence,
  FirecrawlAdapterOptions,
  LogoCandidate,
  NormalizedAssetSignals,
  NormalizedColorSignals,
  NormalizedComponentSignals,
  NormalizedConsistencySignals,
  NormalizedLayoutSignals,
  NormalizedLogoSignals,
  NormalizedTypographySignals,
  ScreenshotSignal,
  TypographySignal,
  VisualAcquisitionAdapter,
  VisualAcquisitionResult,
  VisualAssetCandidate,
  VisualSignature,
  VisualSignatureAdapterName,
  VisualSignatureInput,
  VisualSignatureOptions,
  VisualSignalSource,
} from "./types";
