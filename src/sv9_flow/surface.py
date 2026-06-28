"""Surface taxonomy for reducing pre-SV9 authority.

The purpose of this module is not to run a new scanner. It names the roles that
current and future modules may play so we can split orchestrators/workers
without letting intermediate scorers become product authorities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SurfaceRole = Literal[
    "acquisition",
    "evidence",
    "interpretation",
    "tile_signal",
    "sv9_score",
    "view",
    "debug",
    "legacy_score",
]

WorkerKind = Literal["orchestrator", "worker", "facade", "view", "legacy"]

PreSv9AllowedRole = Literal["acquisition", "evidence", "interpretation", "tile_signal", "debug"]

PRE_SV9_ALLOWED_ROLES: set[str] = {
    "acquisition",
    "evidence",
    "interpretation",
    "tile_signal",
    "debug",
}


@dataclass(frozen=True, slots=True)
class SurfaceArtifact:
    name: str
    current_role: SurfaceRole
    target_role: SurfaceRole
    worker_kind: WorkerKind
    produces_brand_score: bool = False
    canonical_before_sv9: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


CURRENT_SURFACE_INVENTORY: tuple[SurfaceArtifact, ...] = (
    SurfaceArtifact(
        name="SV9 scan",
        current_role="sv9_score",
        target_role="sv9_score",
        worker_kind="orchestrator",
        produces_brand_score=True,
        canonical_before_sv9=False,
        notes="Canonical final scoring surface.",
    ),
    SurfaceArtifact(
        name="Magnetism score",
        current_role="legacy_score",
        target_role="debug",
        worker_kind="legacy",
        produces_brand_score=True,
        canonical_before_sv9=False,
        notes="Useful for regression comparison, not as upstream authority.",
    ),
    SurfaceArtifact(
        name="MagnetismExtractor",
        current_role="interpretation",
        target_role="interpretation",
        worker_kind="facade",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Compatibility facade for future brand interpretation worker.",
    ),
    SurfaceArtifact(
        name="Pass 1",
        current_role="interpretation",
        target_role="interpretation",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Pinned detection/interpretation artifact, not a product score.",
    ),
    SurfaceArtifact(
        name="tldr_brand3",
        current_role="interpretation",
        target_role="interpretation",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Candidate future name: brand_interpretation_v1.",
    ),
    SurfaceArtifact(
        name="Research Pack",
        current_role="evidence",
        target_role="evidence",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Evidence contract input for interpretation.",
    ),
    SurfaceArtifact(
        name="EvidenceGraph / Evidence vNext",
        current_role="evidence",
        target_role="evidence",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Candidate evidence builder behind facade until stable.",
    ),
    SurfaceArtifact(
        name="Visual Signature evidence",
        current_role="evidence",
        target_role="tile_signal",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Evidence-only visual packet; may emit tile signals.",
    ),
    SurfaceArtifact(
        name="Visual Signature score",
        current_role="legacy_score",
        target_role="debug",
        worker_kind="legacy",
        produces_brand_score=True,
        canonical_before_sv9=False,
        notes="Diagnostic only; should not feed SV9 as a score.",
    ),
    SurfaceArtifact(
        name="sv9_visual_evidence",
        current_role="evidence",
        target_role="debug",
        worker_kind="legacy",
        produces_brand_score=False,
        canonical_before_sv9=False,
        notes="Fallback/debug once Visual Signature evidence is reliable.",
    ),
    SurfaceArtifact(
        name="SV9 tile signals",
        current_role="tile_signal",
        target_role="tile_signal",
        worker_kind="worker",
        produces_brand_score=False,
        canonical_before_sv9=True,
        notes="Main integration boundary before final SV9 evaluation.",
    ),
)


def pre_sv9_authority_violations(
    inventory: tuple[SurfaceArtifact, ...] = CURRENT_SURFACE_INVENTORY,
) -> list[SurfaceArtifact]:
    """Return artifacts that would wrongly have canonical authority before SV9."""

    violations: list[SurfaceArtifact] = []
    for artifact in inventory:
        if not artifact.canonical_before_sv9:
            continue
        if artifact.target_role not in PRE_SV9_ALLOWED_ROLES:
            violations.append(artifact)
            continue
        if artifact.produces_brand_score:
            violations.append(artifact)
    return violations


def worker_artifacts(
    inventory: tuple[SurfaceArtifact, ...] = CURRENT_SURFACE_INVENTORY,
) -> list[SurfaceArtifact]:
    """Artifacts that should evolve as testable workers, not product surfaces."""

    return [
        artifact
        for artifact in inventory
        if artifact.worker_kind == "worker" and artifact.target_role in PRE_SV9_ALLOWED_ROLES
    ]


def legacy_score_artifacts(
    inventory: tuple[SurfaceArtifact, ...] = CURRENT_SURFACE_INVENTORY,
) -> list[SurfaceArtifact]:
    """Intermediate scoring surfaces that should be kept out of the canonical path."""

    return [
        artifact
        for artifact in inventory
        if artifact.current_role == "legacy_score" or artifact.produces_brand_score and artifact.target_role != "sv9_score"
    ]
