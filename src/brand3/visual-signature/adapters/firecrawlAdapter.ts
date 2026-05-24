import type {
  FirecrawlAdapterOptions,
  VisualAcquisitionAdapter,
  VisualAcquisitionResult,
  VisualAssetCandidate,
  VisualSignatureInput,
} from "../types";

type FirecrawlScrapeResponse = {
  success?: boolean;
  data?: {
    markdown?: string;
    html?: string;
    rawHtml?: string;
    links?: unknown[];
    images?: unknown[];
    screenshot?: string;
    metadata?: Record<string, unknown>;
    warning?: string;
  };
  error?: string;
  message?: string;
};

const DEFAULT_ENDPOINT = "https://api.firecrawl.dev/v2/scrape";
const DEFAULT_TIMEOUT_MS = 60_000;

export class FirecrawlVisualSignatureAdapter implements VisualAcquisitionAdapter {
  readonly name = "firecrawl" as const;

  private readonly apiKey?: string;
  private readonly endpoint: string;
  private readonly timeoutMs: number;
  private readonly waitForMs: number;
  private readonly includeScreenshot: boolean;
  private readonly includeImages: boolean;
  private readonly zeroDataRetention: boolean;
  private readonly fetchImpl: typeof fetch;

  constructor(options: FirecrawlAdapterOptions = {}) {
    this.apiKey = options.apiKey ?? readEnv("FIRECRAWL_API_KEY");
    this.endpoint = options.endpoint ?? DEFAULT_ENDPOINT;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.waitForMs = options.waitForMs ?? 2_000;
    this.includeScreenshot = options.includeScreenshot ?? true;
    this.includeImages = options.includeImages ?? true;
    this.zeroDataRetention = options.zeroDataRetention ?? false;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async acquire(input: VisualSignatureInput): Promise<VisualAcquisitionResult> {
    const acquiredAt = new Date().toISOString();
    if (!this.apiKey) {
      return emptyAcquisition(input, acquiredAt, ["FIRECRAWL_API_KEY not set"]);
    }

    const formats: Array<string | Record<string, unknown>> = [
      "markdown",
      "html",
      "rawHtml",
      "links",
    ];
    if (this.includeImages) {
      formats.push("images");
    }
    if (this.includeScreenshot) {
      formats.push({
        type: "screenshot",
        fullPage: false,
        quality: 80,
        viewport: { width: 1440, height: 1200 },
      });
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs + 5_000);
    try {
      const response = await this.fetchImpl(this.endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: input.websiteUrl,
          formats,
          onlyMainContent: false,
          onlyCleanContent: false,
          removeBase64Images: true,
          blockAds: true,
          waitFor: this.waitForMs,
          timeout: this.timeoutMs,
          zeroDataRetention: this.zeroDataRetention,
        }),
        signal: controller.signal,
      });
      const payload = (await response.json().catch(() => ({}))) as FirecrawlScrapeResponse;
      const data = payload.data ?? {};
      const metadata = data.metadata ?? {};
      const warning = payload.error ?? payload.message ?? data.warning;
      const errors = response.ok && payload.success !== false ? [] : [warning || `Firecrawl request failed: ${response.status}`];
      const warnings = response.ok && warning ? [warning] : [];
      return {
        adapter: this.name,
        requestedUrl: input.websiteUrl,
        finalUrl: stringFrom(metadata.sourceURL) || input.websiteUrl,
        statusCode: numberFrom(metadata.statusCode) ?? response.status,
        renderedHtml: data.html ?? "",
        rawHtml: data.rawHtml ?? "",
        markdown: data.markdown ?? "",
        links: normalizeStringList(data.links),
        images: normalizeImages(data.images),
        screenshot: data.screenshot
          ? {
              url: data.screenshot,
              viewport: { width: 1440, height: 1200, fullPage: false },
              source: "screenshot",
            }
          : undefined,
        metadata,
        warnings,
        errors,
        acquiredAt,
      };
    } catch (error) {
      return emptyAcquisition(input, acquiredAt, [
        error instanceof Error ? error.message : "Firecrawl request failed",
      ]);
    } finally {
      clearTimeout(timeout);
    }
  }
}

function emptyAcquisition(
  input: VisualSignatureInput,
  acquiredAt: string,
  errors: string[],
): VisualAcquisitionResult {
  return {
    adapter: "firecrawl",
    requestedUrl: input.websiteUrl,
    finalUrl: input.websiteUrl,
    links: [],
    images: [],
    metadata: {},
    warnings: [],
    errors,
    acquiredAt,
  };
}

function normalizeImages(value: unknown): VisualAssetCandidate[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item): VisualAssetCandidate | null => {
      if (typeof item === "string") {
        return { url: item, source: "images", roleHint: roleHintFromUrl(item) };
      }
      if (!item || typeof item !== "object") {
        return null;
      }
      const record = item as Record<string, unknown>;
      const url = stringFrom(record.url) || stringFrom(record.src);
      if (!url) {
        return null;
      }
      return {
        url,
        alt: stringFrom(record.alt),
        width: numberFrom(record.width),
        height: numberFrom(record.height),
        source: "images",
        roleHint: roleHintFromUrl(`${url} ${stringFrom(record.alt)}`),
      };
    })
    .filter((item): item is VisualAssetCandidate => Boolean(item));
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function roleHintFromUrl(value: string): VisualAssetCandidate["roleHint"] {
  const lower = value.toLowerCase();
  if (lower.includes("logo") || lower.includes("brandmark") || lower.includes("wordmark")) {
    return "logo";
  }
  if (lower.includes("icon") || lower.includes("favicon")) {
    return "icon";
  }
  if (lower.includes("illustration") || lower.includes("graphic")) {
    return "illustration";
  }
  if (lower.includes("background") || lower.includes("hero")) {
    return "background";
  }
  return "unknown";
}

function readEnv(name: string): string | undefined {
  const maybeProcess = globalThis as typeof globalThis & {
    process?: { env?: Record<string, string | undefined> };
  };
  return maybeProcess.process?.env?.[name];
}

function stringFrom(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function numberFrom(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
    return Number(value);
  }
  return undefined;
}
