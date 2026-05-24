import type {
  NormalizedAssetSignals,
  NormalizedColorSignals,
  NormalizedComponentSignals,
  NormalizedConsistencySignals,
  NormalizedTypographySignals,
} from "../types";

export function normalizeConsistencySignals(input: {
  colors: NormalizedColorSignals;
  typography: NormalizedTypographySignals;
  components: NormalizedComponentSignals;
  assets: NormalizedAssetSignals;
}): NormalizedConsistencySignals {
  const colorConsistency = scoreColorConsistency(input.colors);
  const typographyConsistency = scoreTypographyConsistency(input.typography);
  const componentConsistency = scoreComponentConsistency(input.components);
  const assetConsistency = scoreAssetConsistency(input.assets);
  const overallConsistency = round(
    colorConsistency * 0.3 +
      typographyConsistency * 0.25 +
      componentConsistency * 0.25 +
      assetConsistency * 0.2,
  );
  const notes: string[] = [];

  if (input.colors.paletteComplexity === "high") {
    notes.push("High color variety detected; verify whether this is systemized or incidental.");
  }
  if ((input.typography.fontFamilies?.length ?? 0) > 5) {
    notes.push("Many font families detected in rendered CSS.");
  }
  if (!input.assets.screenshotAvailable) {
    notes.push("No screenshot was available from the acquisition adapter.");
  }

  return {
    colorConsistency,
    typographyConsistency,
    componentConsistency,
    assetConsistency,
    overallConsistency,
    notes,
    confidence: round(
      (input.colors.confidence +
        input.typography.confidence +
        input.components.confidence +
        input.assets.confidence) /
        4,
    ),
  };
}

function scoreColorConsistency(colors: NormalizedColorSignals): number {
  if (!colors.palette.length) return 0.15;
  if (colors.paletteComplexity === "low") return 0.78;
  if (colors.paletteComplexity === "medium") return 0.68;
  return 0.48;
}

function scoreTypographyConsistency(typography: NormalizedTypographySignals): number {
  const familyCount = typography.fontFamilies.length;
  if (!familyCount) return 0.2;
  if (familyCount <= 2) return 0.82;
  if (familyCount <= 5) return 0.65;
  return 0.42;
}

function scoreComponentConsistency(components: NormalizedComponentSignals): number {
  if (!components.components.length) return 0.25;
  const hasNavigation = components.components.some((item) => item.type === "navigation");
  const hasCta = components.components.some((item) => item.type === "cta" || item.type === "button");
  return round(0.42 + (hasNavigation ? 0.2 : 0) + (hasCta ? 0.18 : 0) + Math.min(0.15, components.components.length * 0.02));
}

function scoreAssetConsistency(assets: NormalizedAssetSignals): number {
  if (!assets.imageCount && !assets.svgCount) return 0.2;
  return round(
    0.45 +
      (assets.logoImageCandidates.length ? 0.18 : 0) +
      (assets.iconCandidates.length ? 0.12 : 0) +
      (assets.screenshotAvailable ? 0.12 : 0),
  );
}

function round(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}
