from __future__ import annotations

from typing import Any

from src.features.magnetism.block_interpreters import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    accepted_block_evidence,
    block_evidence_candidates,
    interpret_tldr_block,
    strategic_packet_candidates,
)

from .extractor_data import (
    DECLARATIVE_TLDR_BLOCKS,
    PERFORMED_TLDR_BLOCKS,
    TLDR_KEYS,
    TLDR_TO_LAYER,
    TLDR_BLOCK_CONTRACT,
)
from .extractor_tail import (
    apply_block_specific_content_rules,
    default_counter_evidence,
    default_tldr_mode,
    default_tldr_rationale,
    evidence_list,
    has_tldr_v03_contract,
    infer_claim_type,
    observations_for_block,
    should_recommend_human_review,
)


def derive_tldr(
    layers: dict[str, Any],
    *,
    strategic_packet: dict[str, Any] | None = None,
    brand_context_brief: dict[str, Any] | None = None,
    personality_block_fn=None,
    brand_idea_block_fn=None,
) -> dict[str, Any]:
    tldr: dict[str, Any] = {}
    for key in TLDR_KEYS:
        layer_key = TLDR_TO_LAYER[key]
        layer = layers[layer_key]

        if key in TLDR_BLOCK_INTERPRETER_SPECS:
            interpreted = interpret_tldr_block_from_spec(
                key,
                layers,
                strategic_packet=strategic_packet,
                brand_context_brief=brand_context_brief,
            )
            tldr[key] = with_tldr_contract(key, interpreted or empty_tldr_block(key, layer_key), layers)
            continue

        content: Any = tldr_content_from_layer(layer) if layer["detected"] else None
        evidence = evidence_list(layer.get("evidence")) if layer["detected"] else []
        confidence = layer.get("confidence") if layer["detected"] else "insufficient"
        mode = default_tldr_mode(key, layer)
        rationale = default_tldr_rationale(key, mode)
        if content and evidence:
            content, mode, rationale = apply_block_specific_content_rules(
                key, content, evidence, mode, rationale
            )

        if key == "personality" and not content and personality_block_fn is not None:
            personality = personality_block_fn(layers)
            if personality:
                tldr[key] = with_tldr_contract(key, personality, layers)
                continue

        if key == "brand_idea" and not content and brand_idea_block_fn is not None:
            brand_idea = brand_idea_block_fn(layers)
            if brand_idea:
                tldr[key] = with_tldr_contract(key, brand_idea, layers)
                continue

        if key in {"attributes", "values"} and (content or evidence or layer["detected"]):
            from .extractor_tail import extract_three_terms, joined_layer_evidence

            attribute_text = joined_layer_evidence(
                layers, ["ambientspace", "aetherspace", "netspace", "mindspace"]
            )
            seed_content = "" if content is None else str(content)
            content = extract_three_terms(" ".join([attribute_text, seed_content, *evidence]), key)
            if not content:
                content = None

        block = {
            "content": content,
            "detected": bool(content),
            "mode": mode if content else "not_detected",
            "confidence": confidence if content else "insufficient",
            "evidence": evidence if content else [],
            "rationale": rationale if content else "Insufficient evidence to articulate this block responsibly.",
            "source_layers": [layer_key],
            "human_review_recommended": False,
        }
        tldr[key] = with_tldr_contract(key, block, layers)
    return tldr


def interpret_tldr_block_from_spec(
    key: str,
    layers: dict[str, Any],
    *,
    strategic_packet: dict[str, Any] | None = None,
    brand_context_brief: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS[key]
    candidates = block_evidence_candidates(
        key,
        spec,
        layers,
        strategic_packet,
        TLDR_TO_LAYER[key],
        brand_context_brief,
    )
    return interpret_tldr_block(key, spec, candidates, layers, TLDR_TO_LAYER[key])


def empty_tldr_block(key: str, layer_key: str) -> dict[str, Any]:
    return {
        "content": None,
        "detected": False,
        "mode": "not_detected",
        "confidence": "insufficient",
        "evidence": [],
        "rationale": "Insufficient evidence to articulate this block responsibly.",
        "source_layers": [layer_key],
        "human_review_recommended": False,
    }


def tldr_content_from_layer(layer: dict[str, Any]) -> str | None:
    finding = str(layer.get("finding") or "").strip()
    evidence = str(layer.get("evidence") or "").strip()
    if finding and not finding.startswith("Detected "):
        return finding
    return evidence or finding or None


def with_tldr_contract(
    key: str,
    block: dict[str, Any],
    layers: dict[str, Any],
) -> dict[str, Any]:
    contract = TLDR_BLOCK_CONTRACT[key]
    detected = bool(block.get("detected"))
    evidence_used = evidence_list(block.get("evidence") or block.get("evidence_used"))
    confidence = block.get("confidence") or ("low" if not detected else "medium")
    mode = str(block.get("mode") or ("not_detected" if not detected else "interpreted_from_discourse"))
    if not detected:
        mode = "not_detected"

    claim_type = str(block.get("claim_type") or infer_claim_type(key, mode, detected))
    observations = block.get("observations")
    if not isinstance(observations, list) or not observations:
        observations = observations_for_block(key, evidence_used, block.get("content"))

    counter_evidence = block.get("counter_evidence")
    if not isinstance(counter_evidence, list):
        counter_evidence = []
    if not counter_evidence:
        counter_evidence = default_counter_evidence(key, claim_type, detected, layers)

    human_review = bool(block.get("human_review_recommended"))
    if should_recommend_human_review(key, claim_type, mode, confidence, detected, evidence_used):
        human_review = True

    answer = block.get("answer")
    if answer is None:
        answer = block.get("content")

    upgraded = dict(block)
    upgraded.update(
        {
            "block": key,
            "question": contract["question"],
            "evidence_scope": contract["evidence_scope"],
            "source_signal": contract["source_signal"],
            "source_signal_path": contract["source_signal_path"],
            "source_layer": contract["source_layer"],
            "observations": observations,
            "answer": answer,
            "claim_type": claim_type,
            "mode": mode,
            "confidence": confidence,
            "reasoning": block.get("reasoning") or block.get("rationale"),
            "evidence_used": evidence_used,
            "counter_evidence": counter_evidence,
            "human_review_recommended": human_review,
            "content": block.get("content"),
            "evidence": evidence_used,
            "rationale": block.get("rationale") or block.get("reasoning"),
        }
    )
    return upgraded
