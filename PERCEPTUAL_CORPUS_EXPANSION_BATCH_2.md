# Brand3 Perceptual Corpus Expansion Batch 2

Status: controlled research expansion

## Purpose

Batch 2 expands the perceptual corpus with three more records while preserving the same constraints:

- do not connect the corpus to scoring
- do not modify Phase Zero, Phase One, or Phase Two
- do not let review-only records become stable hint material

## Added cases

### 1. SOVA - Analysis

- canonical source: `https://app.notion.com/p/1f8a44dc3505818894ecf19142ae93a5`
- normalized status: `normalized`
- role: stable crypto strategy summary

### 2. SOVA - Prueba LLM Estrategia

- canonical source: `https://app.notion.com/p/200a44dc35058079996cf0643ff113e7`
- normalized status: `needs_human_review`
- role: review-only LLM strategy experiment

### 3. Eaship - Brand3 Magnetism Scan

- canonical source: `https://app.notion.com/p/35ea44dc3505810b9a10ca1d15f43506`
- normalized status: `normalized`
- role: non-web3 / non-crypto scanner record

## Pattern and hint rules

- Do not add new patterns unless the evidence requires them.
- Keep crypto and experiment-specific language isolated in `domain_specific_noise`.
- Use only `normalized` records for stable narrative hints.
- Keep `needs_human_review` records out of stable hint generation.

## Corpus impact

- The corpus gains one non-web3/non-crypto case for diversity.
- The corpus gains one additional normalized crypto case.
- The corpus keeps one experimental record review-only.
- No scoring behavior changed.
- Phase Zero, Phase One, and Phase Two remain untouched.
