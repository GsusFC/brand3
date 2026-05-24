export type VisualSignatureAdapterName =
  | "firecrawl"
  | "playwright"
  | "browserbase"
  | "vision"
  | "brandfetch"
  | "custom";

export type VisualSignalSource =
  | "rendered_html"
  | "raw_html"
  | "markdown"
  | "links"
  | "images"
  | "screenshot"
  | "metadata"
  | "adapter";

export interface VisualSignatureInput {
  brandName: string;
  websiteUrl: string;
}

export interface VisualSignatureOptions {
  adapter?: VisualAcquisitionAdapter;
  firecrawl?: FirecrawlAdapterOptions;
  now?: Date;
}

export interface FirecrawlAdapterOptions {
  apiKey?: string;
  endpoint?: string;
  timeoutMs?: number;
  waitForMs?: number;
  includeScreenshot?: boolean;
  includeImages?: boolean;
  zeroDataRetention?: boolean;
  fetchImpl?: typeof fetch;
}

export interface VisualAcquisitionAdapter {
  readonly name: VisualSignatureAdapterName;
  acquire(input: VisualSignatureInput): Promise<VisualAcquisitionResult>;
}

export interface VisualAcquisitionResult {
  adapter: VisualSignatureAdapterName;
  requestedUrl: string;
  finalUrl?: string;
  statusCode?: number;
  renderedHtml?: string;
  rawHtml?: string;
  markdown?: string;
  links: string[];
  images: VisualAssetCandidate[];
  screenshot?: ScreenshotSignal;
  metadata: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  acquiredAt: string;
}

export interface VisualAssetCandidate {
  url: string;
  alt?: string;
  width?: number;
  height?: number;
  source: VisualSignalSource;
  roleHint?: "logo" | "icon" | "illustration" | "photo" | "background" | "unknown";
}

export interface ScreenshotSignal {
  url: string;
  viewport?: {
    width?: number;
    height?: number;
    fullPage?: boolean;
  };
  expiresAt?: string;
  source: VisualSignalSource;
}

export interface ColorSignal {
  hex: string;
  role: "background" | "text" | "accent" | "border" | "surface" | "unknown";
  occurrences: number;
  source: VisualSignalSource;
  confidence: number;
}

export interface NormalizedColorSignals {
  palette: ColorSignal[];
  dominantColors: string[];
  accentCandidates: string[];
  backgroundCandidates: string[];
  textColorCandidates: string[];
  paletteComplexity: "low" | "medium" | "high" | "unknown";
  confidence: number;
}

export interface TypographySignal {
  family: string;
  role: "heading" | "body" | "display" | "ui" | "unknown";
  occurrences: number;
  source: VisualSignalSource;
  confidence: number;
}

export interface NormalizedTypographySignals {
  fontFamilies: TypographySignal[];
  headingScale: "flat" | "moderate" | "expressive" | "unknown";
  weightRange: {
    min?: number;
    max?: number;
  };
  sizeSamplesPx: number[];
  confidence: number;
}

export interface LogoCandidate {
  url?: string;
  text?: string;
  alt?: string;
  location: "header" | "nav" | "footer" | "metadata" | "body" | "unknown";
  source: VisualSignalSource;
  confidence: number;
}

export interface NormalizedLogoSignals {
  logoDetected: boolean;
  candidates: LogoCandidate[];
  faviconDetected: boolean;
  textualBrandMarkDetected: boolean;
  primaryLocation: LogoCandidate["location"];
  confidence: number;
}

export interface NormalizedLayoutSignals {
  hasHeader: boolean;
  hasNavigation: boolean;
  hasHero: boolean;
  hasMainContent: boolean;
  hasFooter: boolean;
  sectionCount: number;
  layoutPatterns: Array<"single_column" | "multi_column" | "grid" | "flex" | "sticky_nav" | "unknown">;
  visualDensity: "sparse" | "balanced" | "dense" | "unknown";
  confidence: number;
}

export interface ComponentSignal {
  type:
    | "navigation"
    | "button"
    | "card"
    | "form"
    | "cta"
    | "accordion"
    | "tabs"
    | "modal"
    | "pricing"
    | "unknown";
  count: number;
  labels: string[];
  source: VisualSignalSource;
  confidence: number;
}

export interface NormalizedComponentSignals {
  components: ComponentSignal[];
  primaryCtas: string[];
  interactionPatterns: Array<"form" | "navigation" | "accordion" | "tabs" | "modal" | "unknown">;
  confidence: number;
}

export interface NormalizedAssetSignals {
  imageCount: number;
  svgCount: number;
  videoCount: number;
  backgroundImageCount: number;
  logoImageCandidates: VisualAssetCandidate[];
  iconCandidates: VisualAssetCandidate[];
  screenshotAvailable: boolean;
  assetMix: Array<"logo" | "icon" | "illustration" | "photo" | "video" | "screenshot" | "unknown">;
  confidence: number;
}

export interface NormalizedConsistencySignals {
  colorConsistency: number;
  typographyConsistency: number;
  componentConsistency: number;
  assetConsistency: number;
  overallConsistency: number;
  notes: string[];
  confidence: number;
}

export interface ExtractionConfidence {
  score: number;
  level: "low" | "medium" | "high";
  factors: {
    acquisition: number;
    htmlCoverage: number;
    signalCoverage: number;
    consistencyCoverage: number;
  };
  limitations: string[];
}

export interface VisualSignature {
  brandName: string;
  websiteUrl: string;
  analyzedUrl: string;
  acquisition: {
    adapter: VisualSignatureAdapterName;
    statusCode?: number;
    acquiredAt: string;
    warnings: string[];
    errors: string[];
  };
  colors: NormalizedColorSignals;
  typography: NormalizedTypographySignals;
  logo: NormalizedLogoSignals;
  layout: NormalizedLayoutSignals;
  components: NormalizedComponentSignals;
  assets: NormalizedAssetSignals;
  consistency: NormalizedConsistencySignals;
  extractionConfidence: ExtractionConfidence;
  version: "visual-signature-mvp-1";
}
