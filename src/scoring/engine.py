"""
Brand3 Scoring Engine

Weighted linear scoring + heuristic rules.
Input: extracted features per dimension
Output: BrandScore with 0-100 per dimension + composite

Philosophy:
- Scores are 0-100 per dimension
- Heuristic rules can cap scores (never boost above what data supports)
- Composite is weighted average of dimensions
- Every score comes with an explanation of why
"""

import copy
from dataclasses import dataclass
from ..models.brand import BrandScore, DimensionScore, FeatureValue
from ..dimensions import DIMENSIONS
from ..niche.profiles import get_calibration_profile


@dataclass
class ScoringRule:
    """A heuristic rule that can override/cap scores."""
    condition: str  # human-readable
    check: callable  # fn(features) -> bool
    cap: float  # max score if rule fires
    insight: str  # explanation for the user


class ScoringEngine:
    """Core scoring engine. Weighted linear + heuristic rules."""

    def __init__(self, calibration_profile: str = "base"):
        self.calibration_profile = calibration_profile or "base"
        self.profile_config = get_calibration_profile(self.calibration_profile)
        self.dimensions = self._build_dimensions()
        self.rules = self._build_rules()

    def _build_dimensions(self) -> dict:
        dimensions = copy.deepcopy(DIMENSIONS)
        weights = self.profile_config.get("dimension_weights", {})
        for dim_name, weight in weights.items():
            if dim_name in dimensions:
                dimensions[dim_name]["weight"] = float(weight)
        return dimensions

    def _rule_override(self, dim_name: str, condition: str) -> dict:
        return (
            self.profile_config.get("rule_overrides", {})
            .get(dim_name, {})
            .get(condition, {})
        )

    def _build_rules(self) -> dict[str, list[ScoringRule]]:
        """Build heuristic rules from dimension definitions."""
        ghost = self._rule_override("presencia", "marca_fantasma")
        low_mentions = self._rule_override("percepcion", "sin_datos_suficientes")
        generic = self._rule_override("diferenciacion", "lenguaje_generico")
        inactive_6m = self._rule_override("vitalidad", "inactiva_6m")
        inactive_12m = self._rule_override("vitalidad", "inactiva_12m")
        no_web = self._rule_override("coherencia", "sin_web_propia")
        one_channel = self._rule_override("coherencia", "solo_un_canal_activo")
        return {
            "coherencia": [
                ScoringRule(
                    condition="sin_web_propia",
                    check=lambda f, threshold=float(no_web.get("threshold", 20)): (
                        f.get("web_presence", FeatureValue("", 0)).value < threshold
                    ),
                    cap=float(no_web.get("cap", 40)),
                    insight="Sin web propia, la coherencia de marca está limitada",
                ),
                ScoringRule(
                    condition="solo_un_canal_activo",
                    check=lambda f,
                    web_threshold=float(one_channel.get("web_threshold", 20)),
                    social_threshold=float(one_channel.get("social_threshold", 20)),
                    search_threshold=float(one_channel.get("search_threshold", 25)): (
                        sum(
                            [
                                f.get("web_presence", FeatureValue("", 0)).value >= web_threshold,
                                f.get("social_footprint", FeatureValue("", 0)).value >= social_threshold,
                                f.get("search_visibility", FeatureValue("", 0)).value >= search_threshold,
                            ]
                        ) <= 1
                    ),
                    cap=float(one_channel.get("cap", 50)),
                    insight="Solo hay un canal activo detectable — la coherencia cross-channel está limitada",
                ),
            ],
            "presencia": [
                ScoringRule(
                    condition="marca_fantasma",
                    check=lambda f,
                    web_threshold=float(ghost.get("web_threshold", 10)),
                    social_threshold=float(ghost.get("social_threshold", 10)): (
                        f.get("web_presence", FeatureValue("", 0)).value < web_threshold
                        and f.get("social_footprint", FeatureValue("", 0)).value < social_threshold
                    ),
                    cap=float(ghost.get("cap", 5)),
                    insight="Sin web ni socials detectables — marca fantasma",
                ),
            ],
            "percepcion": [
                ScoringRule(
                    condition="sin_datos_suficientes",
                    check=lambda f, threshold=float(low_mentions.get("threshold", 10)): (
                        f.get("mention_volume", FeatureValue("", 0)).value < threshold
                    ),
                    cap=float(low_mentions.get("cap", 50)),
                    insight="Mentions insuficientes — score neutral (no hay datos)",
                ),
            ],
            "diferenciacion": [
                ScoringRule(
                    condition="lenguaje_generico",
                    check=lambda f, threshold=float(generic.get("threshold", 80)): (
                        f.get("uniqueness", FeatureValue("", 100)).value < (100 - threshold)
                    ),
                    cap=float(generic.get("cap", 25)),
                    insight="Lenguaje excesivamente genérico — baja diferenciación",
                ),
            ],
            "vitalidad": [
                ScoringRule(
                    condition="inactiva_6m",
                    check=lambda f, threshold=float(inactive_6m.get("threshold", 20)): (
                        f.get("content_recency", FeatureValue("", 0)).value < threshold
                    ),
                    cap=float(inactive_6m.get("cap", 20)),
                    insight="Última publicación hace más de 6 meses",
                ),
                ScoringRule(
                    condition="inactiva_12m",
                    check=lambda f, threshold=float(inactive_12m.get("threshold", 10)): (
                        f.get("content_recency", FeatureValue("", 0)).value < threshold
                    ),
                    cap=float(inactive_12m.get("cap", 10)),
                    insight="Última publicación hace más de 12 meses — marca inactiva",
                ),
            ],
        }

    def score_dimension(
        self, dim_name: str, features: dict[str, FeatureValue],
        all_features: dict[str, dict[str, FeatureValue]] = None
    ) -> DimensionScore:
        """Score a single dimension from its features."""
        dim = self.dimensions[dim_name]
        dim_features = dim["features"]

        # Weighted linear: sum(feature_score * feature_weight) * 100
        weighted_sum = 0.0
        total_weight = 0.0

        for feat_name, feat_def in dim_features.items():
            if feat_name in features:
                fv = features[feat_name]
                weighted_sum += fv.value * feat_def["weight"]
                total_weight += feat_def["weight"]

        has_data = total_weight > 0
        if has_data:
            raw_score = (weighted_sum / total_weight)
        else:
            raw_score = 50.0  # neutral if no data

        # For rule checks, merge all features so cross-dimension rules work
        merged_features = {}
        if all_features:
            for dim_feats in all_features.values():
                merged_features.update(dim_feats)
        merged_features.update(features)

        # Apply heuristic rules (caps)
        rules_applied = []
        insights = []
        for rule in self.rules.get(dim_name, []):
            if has_data and rule.check(merged_features):
                if raw_score > rule.cap:
                    raw_score = rule.cap
                rules_applied.append(rule.condition)
                insights.append(rule.insight)

        # Clamp to 0-100
        raw_score = max(0.0, min(100.0, raw_score))

        return DimensionScore(
            name=dim_name,
            score=round(raw_score, 1),
            features=features,
            insights=insights,
            rules_applied=rules_applied,
        )

    def score_brand(
        self,
        url: str,
        brand_name: str,
        features_by_dim: dict[str, dict[str, FeatureValue]],
    ) -> BrandScore:
        """Score a complete brand across all dimensions."""
        brand = BrandScore(url=url, brand_name=brand_name)

        for dim_name, dim_def in self.dimensions.items():
            dim_features = features_by_dim.get(dim_name, {})
            brand.dimensions[dim_name] = self.score_dimension(
                dim_name, dim_features, all_features=features_by_dim
            )

        # Composite: weighted average of dimension scores
        composite = 0.0
        for dim_name, dim_def in self.dimensions.items():
            composite += brand.dimensions[dim_name].score * dim_def["weight"]

        brand.composite_score = round(composite, 1)

        return brand

    def generate_summary(self, brand: BrandScore) -> str:
        """Generate human-readable summary of the score."""
        lines = []
        lines.append(f"=== {brand.brand_name} ===")
        lines.append(f"URL: {brand.url}")
        lines.append(f"Score Global: {brand.composite_score}/100")
        lines.append("")

        # Sort dimensions by score (weakest first — what needs work)
        sorted_dims = sorted(brand.dimensions.items(), key=lambda x: x[1].score)

        for dim_name, dim in sorted_dims:
            bar = "█" * int(dim.score / 5) + "░" * (20 - int(dim.score / 5))
            lines.append(f"  {dim_name:15s} {bar} {dim.score:5.1f}")
            for insight in dim.insights:
                lines.append(f"    ⚠ {insight}")

        lines.append("")

        # Top weakness
        weakest = sorted_dims[0]
        lines.append(f"Punto débil: {weakest[0]} ({weakest[1].score}/100)")

        # Top strength
        strongest = sorted_dims[-1]
        lines.append(f"Punto fuerte: {strongest[0]} ({strongest[1].score}/100)")

        return "\n".join(lines)
