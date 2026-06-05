"""
LLM-based brand analysis.

Uses LLM to make subjective judgments that keyword matching can't:
- Is the brand's language unique or generic?
- What category/positioning does the brand claim?
- How does third-party perception compare to self-description?
- What are the brand's distinctive concepts?

Provider is configured via src.config (OpenAI-compatible API).
"""

import json
import hashlib
import multiprocessing as mp
import os
import queue
import socket
import urllib.request
import urllib.error
from typing import Any

from src.config import BRAND3_DB_PATH, BRAND3_LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


PROMPT_VERSION = "brand3-llm-v1"
LLM_CALL_TIMEOUT_SECONDS = int(os.environ.get("BRAND3_LLM_CALL_TIMEOUT_SECONDS", "35"))
STRUCTURED_RESEARCH_PACK_LIMIT = 6000


def _llm_prompt_input(value: str, *, default_limit: int) -> str:
    """Preserve structured evidence packs while keeping legacy raw markdown bounded."""
    text = value or ""
    limit = STRUCTURED_RESEARCH_PACK_LIMIT if text.lstrip().startswith("Structured Brand Research Pack") else default_limit
    return text[:limit]


def _looks_like_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(exc).lower() or "timeout" in str(exc).lower()


def _llm_http_worker(output_queue, url: str, payload: bytes, headers: dict[str, str], timeout_seconds: int) -> None:
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read())
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning") or ""
            output_queue.put(("ok", content))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        output_queue.put(("error", f"HTTP {exc.code}: {error_body}"))
    except Exception as exc:
        reason = "timeout" if _looks_like_timeout(exc) else "error"
        output_queue.put((reason, str(exc)))


def _run_llm_http_call(
    *,
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[str, str]:
    if timeout_seconds <= 0:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=None) as resp:
            data = json.loads(resp.read())
            msg = data["choices"][0]["message"]
            return "ok", msg.get("content") or msg.get("reasoning") or ""

    import sys
    method = "spawn" if sys.platform == "darwin" else ("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    ctx = mp.get_context(method)
    output_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_llm_http_worker,
        args=(output_queue, url, payload, headers, timeout_seconds),
    )
    process.start()
    process.join(timeout_seconds + 2)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        return "timeout", f"llm_call_timeout_after_{timeout_seconds}s"

    try:
        status, content = output_queue.get_nowait()
    except queue.Empty:
        return "error", "llm_call_no_result"
    return str(status), str(content or "")


def llm_failure_reason(llm, default: str) -> str:
    reason = getattr(llm, "last_failure_reason", None)
    if reason in {"llm_timeout", "llm_error"}:
        return reason
    return default


def _provider_error_payload(error: str) -> dict[str, object]:
    text = error or ""
    http_status = None
    body = text
    if text.startswith("HTTP "):
        prefix, _, rest = text.partition(":")
        parts = prefix.split()
        if len(parts) >= 2:
            try:
                http_status = int(parts[1])
            except ValueError:
                http_status = None
        body = rest.strip()

    provider_error_code = None
    provider_error_message = None
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        err = parsed.get("error")
        if isinstance(err, dict):
            provider_error_code = err.get("code") or err.get("status") or err.get("type")
            provider_error_message = err.get("message") or err.get("error")
        else:
            provider_error_code = parsed.get("code") or parsed.get("status") or parsed.get("type")
            provider_error_message = parsed.get("message") or parsed.get("error_description")

    return {
        "http_status": http_status,
        "provider_error_code": str(provider_error_code) if provider_error_code else None,
        "provider_error_message": str(provider_error_message)[:500] if provider_error_message else None,
    }


def _llm_error_type(reason: str, error: str) -> str:
    normalized = (error or "").lower()
    if reason == "llm_timeout" or "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if (error or "").startswith("HTTP "):
        return "http_error"
    if "llm_call_no_result" in normalized:
        return "no_result"
    return "provider_error"


def _json_response_format(
    *,
    json_schema: dict[str, Any] | None = None,
    schema_name: str | None = None,
    strict_schema: bool = True,
) -> dict[str, Any]:
    if not json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name or "brand3_json_response",
            "strict": bool(strict_schema),
            "schema": json_schema,
        },
    }


class LLMAnalyzer:
    """LLM-powered brand content analyzer."""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or BRAND3_LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_writes = 0
        self.timeout_seconds = LLM_CALL_TIMEOUT_SECONDS
        self.last_failure_reason: str | None = None
        self.call_failures: list[dict[str, Any]] = []

    def _record_failure(
        self,
        reason: str,
        error: str,
        *,
        error_type: str | None = None,
        response_empty: bool = False,
        json_parse_error: bool = False,
    ) -> None:
        self.last_failure_reason = reason
        provider_payload = _provider_error_payload(error)
        self.call_failures.append({
            "reason": reason,
            "error": error[:200],
            "error_type": error_type or _llm_error_type(reason, error),
            "http_status": provider_payload["http_status"],
            "provider_error_code": provider_payload["provider_error_code"],
            "provider_error_message": provider_payload["provider_error_message"],
            "response_empty": bool(response_empty),
            "json_parse_error": bool(json_parse_error),
            "model": self.model,
            "base_url": self.base_url,
        })

    def _clear_failure(self) -> None:
        self.last_failure_reason = None

    def _cache_key(
        self,
        response_type: str,
        system: str,
        user: str,
        max_tokens: int,
        *,
        schema_name: str | None = None,
    ) -> str:
        payload = {
            "prompt_version": PROMPT_VERSION,
            "model": self.model,
            "response_type": response_type,
            "schema_name": schema_name or "",
            "system": system,
            "user": user,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return digest

    def _cache_get(self, cache_key: str, response_type: str):
        try:
            from src.storage.sqlite_store import SQLiteStore
            store = SQLiteStore(BRAND3_DB_PATH)
            try:
                cached = store.get_llm_cache(cache_key)
            finally:
                store.close()
        except Exception:
            return None
        if not cached or cached.get("response_type") != response_type:
            return None
        self.cache_hits += 1
        if response_type == "json":
            return cached.get("response_json") or {}
        return cached.get("response_text") or ""

    def _cache_save(self, cache_key: str, response_type: str, value) -> None:
        if value in ("", None, {}):
            return
        try:
            from src.storage.sqlite_store import SQLiteStore
            store = SQLiteStore(BRAND3_DB_PATH)
            try:
                store.save_llm_cache(
                    cache_key=cache_key,
                    prompt_version=PROMPT_VERSION,
                    model=self.model,
                    response_type=response_type,
                    response_json=value if response_type == "json" else None,
                    response_text=value if response_type == "text" else None,
                )
            finally:
                store.close()
            self.cache_writes += 1
        except Exception:
            return

    def _call(self, system: str, user: str, max_tokens: int = 8000) -> str:
        """Make an LLM call via the OpenAI-compatible endpoint.

        Default `max_tokens` is wide enough to accommodate thinking models
        (Gemini 3.x) that consume part of the budget on internal reasoning
        before emitting content.
        """
        if not self.api_key:
            return ""

        cache_key = self._cache_key("text", system, user, max_tokens)
        cached = self._cache_get(cache_key, "text")
        if cached is not None:
            self._clear_failure()
            return cached
        self.cache_misses += 1

        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        payload = json.dumps(body).encode()

        status, content = _run_llm_http_call(
            url=f"{self.base_url}/chat/completions",
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout_seconds=self.timeout_seconds,
        )
        if status == "ok":
            if not content:
                self._record_failure(
                    "llm_error",
                    "empty_provider_response",
                    error_type="empty_response",
                    response_empty=True,
                )
                return ""
            self._clear_failure()
            self._cache_save(cache_key, "text", content)
            return content

        reason = "llm_timeout" if status == "timeout" else "llm_error"
        self._record_failure(reason, content)
        print(f"  LLM call failed: {content}")
        return ""

    def _call_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
        *,
        json_schema: dict[str, Any] | None = None,
        schema_name: str | None = None,
        strict_schema: bool = True,
        timeout_seconds: int | None = None,
    ) -> dict:
        """Make an LLM call expecting strict JSON response.

        Uses JSON mode by default. When `json_schema` is provided, uses the
        OpenAI-compatible `json_schema` response_format and falls back to plain
        `json_object` if the provider rejects schema mode.
        """
        if not self.api_key:
            return {}

        normalized_schema_name = schema_name if json_schema else None
        cache_key = self._cache_key("json", system, user, max_tokens, schema_name=normalized_schema_name)
        cached = self._cache_get(cache_key, "json")
        if cached is not None:
            self._clear_failure()
            return cached
        self.cache_misses += 1

        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "response_format": _json_response_format(
                json_schema=json_schema,
                schema_name=schema_name,
                strict_schema=strict_schema,
            ),
        }

        effective_timeout = self.timeout_seconds if timeout_seconds is None else int(timeout_seconds)
        payload = json.dumps(body).encode()
        status, content = _run_llm_http_call(
            url=f"{self.base_url}/chat/completions",
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout_seconds=effective_timeout,
        )
        if status != "ok" and json_schema is not None:
            # Provider compatibility varies; keep production safe by falling back
            # to JSON mode while preserving schema-specific cache separation.
            fallback_body = dict(body)
            fallback_body["response_format"] = {"type": "json_object"}
            status, content = _run_llm_http_call(
                url=f"{self.base_url}/chat/completions",
                payload=json.dumps(fallback_body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout_seconds=effective_timeout,
            )
        if status != "ok":
            reason = "llm_timeout" if status == "timeout" else "llm_error"
            self._record_failure(reason, content)
            print(f"  LLM JSON call failed: {content}")
            return {}

        if not content:
            self._record_failure(
                "llm_error",
                "empty_provider_response",
                error_type="empty_response",
                response_empty=True,
            )
            return {}

        # Belt-and-suspenders: strip markdown fencing if the model still added it.
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        try:
            parsed = json.loads(content)
            self._cache_save(cache_key, "json", parsed)
            self._clear_failure()
            return parsed
        except json.JSONDecodeError as e:
            print(f"  LLM JSON parse failed: {e}; got: {content[:200]}")
            self._record_failure(
                "llm_error",
                str(e),
                error_type="json_parse_error",
                json_parse_error=True,
            )
            return {}

    def analyze_positioning_clarity(
        self, web_content: str, brand_name: str, competitor_snippets: list[str] | None = None
    ) -> dict:
        """LLM judgment for positioning clarity with literal evidence."""
        content = _llm_prompt_input(web_content, default_limit=3000)
        competitor_block = ""
        if competitor_snippets:
            competitor_block = "\n\nCompetitor context:\n---\n" + "\n---\n".join(
                snippet[:500] for snippet in competitor_snippets[:3]
            )

        return self._call_json(
            system=(
                "You are a brand positioning analyst. Return ONLY valid JSON. "
                "You must use literal evidence and respect source boundaries."
            ),
            user=f"""Analyze the positioning clarity of this brand.

Brand: {brand_name}
Evidence input:
---
{content}
---{competitor_block}

Instructions:
- The input may be a Structured Brand Research Pack rather than raw website copy.
- Treat owned/core evidence as the brand's self-description.
- Treat proof points, press, founder context, and third-party mentions as context, not as self-positioning.
- Never use rejected noise, page chrome, navigation, cookie text, or CTAs as positioning evidence.
- Evidence gaps and confidence notes are negative evidence. Use them to lower confidence/verdict when relevant.
- Distinguish:
  - clear: the position is articulated concretely and sustained in the content
  - diffuse: it gestures at a position but loses focus
  - generic: template SaaS language with little real positioning
  - unclear: too little usable owned/self evidence, even if press/proof context exists
- Evidence quotes must be literal snippets from the evidence input, not paraphrases.

Return JSON with this exact structure:
{{
  "clarity_score": 0,
  "verdict": "clear" | "diffuse" | "generic" | "unclear",
  "stated_position": "one sentence",
  "target_audience": "one phrase",
  "differentiator_claimed": "one phrase",
  "evidence": [
    {{"quote": "literal quote", "signal": "clear" | "generic" | "aspirational"}}
  ],
  "reasoning": "1-2 sentences"
}}"""
        )

    def analyze_uniqueness(
        self, web_content: str, brand_name: str, competitor_snippets: list[str] | None = None
    ) -> dict:
        """LLM judgment for brand uniqueness vs generic language."""
        content = _llm_prompt_input(web_content, default_limit=3000)
        competitor_block = ""
        if competitor_snippets:
            competitor_block = "\n\nCompetitor context:\n---\n" + "\n---\n".join(
                snippet[:500] for snippet in competitor_snippets[:3]
            )

        return self._call_json(
            system=(
                "You are a brand differentiation analyst. Return ONLY valid JSON. "
                "Distinguish generic SaaS template language from ownable vocabulary."
            ),
            user=f"""Analyze how unique this brand's language is.

Brand: {brand_name}
Evidence input:
---
{content}
---{competitor_block}

Instructions:
- The input may be a Structured Brand Research Pack rather than raw website copy.
- Judge uniqueness of the brand's own language, not uniqueness of the market category alone.
- Distinguish generic SaaS language ("cutting edge", "seamless", "revolutionary").
- Distinguish empty aspirational language ("we empower", "unlock potential").
- Highlight authentic brand vocabulary and repeated ownable terms.
- Do not mark a brand unique because press/proof points describe traction or funding.
- Use competitor overlap to penalize vocabulary that mirrors category peers.
- Never use rejected noise, page chrome, navigation, cookie text, or CTAs as uniqueness evidence.

Return JSON with this exact structure:
{{
  "uniqueness_score": 0,
  "verdict": "highly_unique" | "moderately_unique" | "derivative" | "generic" | "unclear",
  "unique_phrases": ["phrase"],
  "generic_phrases": ["phrase"],
  "brand_vocabulary": ["term"],
  "competitor_overlap_signals": ["signal"],
  "reasoning": "1-2 sentences"
}}"""
        )

    def analyze_messaging_consistency(
        self,
        web_content: str,
        third_party_mentions: list[dict],
        brand_name: str,
    ) -> dict:
        """Compare self-description (web) with third-party descriptions (mentions).

        Returns verdict with literal quotes in `gaps` as evidence.
        """
        # REVIEW: método nuevo para messaging_consistency de coherencia.
        if not web_content or not isinstance(third_party_mentions, list):
            return {}

        content = _llm_prompt_input(web_content, default_limit=3000)
        lines = []
        for i, m in enumerate(third_party_mentions[:8], start=1):
            text = (m.get("text") or "")[:400].replace("\n", " ").strip()
            url = m.get("url") or ""
            title = (m.get("title") or "").replace("\n", " ").strip()
            source_class = (m.get("source_class") or "unknown").replace("\n", " ").strip()
            relation = (m.get("relation") or "unknown").replace("\n", " ").strip()
            if not text and not title:
                continue
            lines.append(f"[{i}] {url}\nsource_class={source_class}; relation={relation}\n{title}\n{text}")
        mentions_block = "\n---\n".join(lines) if lines else "(no mentions available)"

        return self._call_json(
            system=(
                "You are a brand coherence analyst. Compare how the brand describes "
                "itself against how third parties describe it. You quote sources "
                "literally. Return ONLY valid JSON."
            ),
            user=f"""Analyse whether "{brand_name}" describes itself consistently with how others describe it.

Brand's own website copy:
---
{content}
---

Third-party mentions:
---
{mentions_block}
---

Rules:
- The brand evidence may be a Structured Brand Research Pack. Use it as the self-description side.
- Use only the Third-party mentions section as external perception.
- Do not treat owned claims, proof points, founder context, or rejected noise inside the Research Pack as third-party validation.
- Return literal quotes in `gaps`, not paraphrase.
- If fewer than 2 third-party mentions are useful, return `verdict: "unclear"` and empty `gaps`.
- Mentions with source_class=owned or relation=same_root_surface/audited_surface are not independent; do not count them as useful third-party mentions.
- Ignore mentions that are clearly NOT about "{brand_name}" (scraping false positives).

Return JSON with this exact structure:
{{
    "consistency_score": 0-100,
    "verdict": "aligned" | "partial_gap" | "divergent" | "unclear",
    "self_category": "how the brand describes itself in one phrase",
    "third_party_category": "how others describe it in one phrase",
    "aligned_themes": ["themes both agree on"],
    "gaps": [
        {{"self_says": "literal quote from website", "third_party_says": "literal quote from a mention", "source_url": "the mention url"}}
    ],
    "reasoning": "1-2 sentences explaining the verdict"
}}"""
        )

    def analyze_tone_consistency(
        self,
        web_content: str,
        third_party_snippets: list[dict],
        brand_name: str,
    ) -> dict:
        """Assess whether tone on the brand's surface matches third-party tone."""
        # REVIEW: método nuevo para tone_consistency de coherencia.
        if not web_content:
            return {}

        content = _llm_prompt_input(web_content, default_limit=2500)
        lines = []
        for i, m in enumerate((third_party_snippets or [])[:5], start=1):
            text = (m.get("text") or "")[:300].replace("\n", " ").strip()
            url = m.get("url") or ""
            source_class = (m.get("source_class") or "unknown").replace("\n", " ").strip()
            relation = (m.get("relation") or "unknown").replace("\n", " ").strip()
            if not text:
                continue
            lines.append(f"[{i}] {url}\nsource_class={source_class}; relation={relation}\n{text}")
        mentions_block = "\n---\n".join(lines) if lines else "(no third-party snippets)"

        return self._call_json(
            system=(
                "You are a brand tone analyst. Describe the tone of the brand's own "
                "copy and the tone of third-party mentions, and judge whether they "
                "match. Quote sources literally. Return ONLY valid JSON."
            ),
            user=f"""Assess tone consistency for "{brand_name}".

Brand's own website copy:
---
{content}
---

Third-party mentions:
---
{mentions_block}
---

Rules:
- The brand evidence may be a Structured Brand Research Pack. Use it as the brand's own tone side.
- Use only the Third-party mentions section for external tone.
- Tone examples MUST be literal quotes.
- Return `gap_signal: "none"` only when brand tone and at least one useful independent mention tone are visibly aligned.
- If no useful third-party material, return `gap_signal: "mild"` with conservative reasoning rather than pretending external tone is known.
- If contradictions exist, return `gap_signal: "strong"` and a lower score.
- Do not use rejected noise, page chrome, navigation, cookie text, or CTAs as tone evidence.

Return JSON with this exact structure:
{{
    "tone_consistency_score": 0-100,
    "self_tone": "description of the tone in the website",
    "third_party_tone": "how the mentions sound about the brand",
    "gap_signal": "none" | "mild" | "strong",
    "examples": [
        {{"source": "web" | "mention", "quote": "literal quote", "tone_marker": "what signals the tone"}}
    ],
    "reasoning": "1-2 sentences"
}}"""
        )

    def analyze_brand_sentiment(self, mentions: list[dict], brand_name: str) -> dict:
        """Unified sentiment + controversy analysis for Percepción.

        Reads up to 15 third-party mentions and returns a structured verdict
        with literal quotes as evidence. Flags controversy explicitly so the
        caller can cap the score without needing a separate rule.
        """
        # REVIEW: método nuevo para brand_sentiment de percepcion.
        if not mentions:
            return {}

        lines = []
        for i, m in enumerate(mentions[:15], start=1):
            text = (m.get("text") or "")[:400].replace("\n", " ").strip()
            url = m.get("url") or ""
            title = (m.get("title") or "").replace("\n", " ").strip()
            if not text and not title:
                continue
            lines.append(f"[{i}] {url}\n{title}\n{text}")
        mentions_block = "\n---\n".join(lines) if lines else "(no mentions available)"

        return self._call_json(
            system=(
                "You are a brand perception analyst. Read third-party mentions "
                "and decide whether public sentiment towards the brand is "
                "positive, mixed, negative, or unclear. Flag serious "
                "controversies separately from ordinary product criticism. "
                "Quote sources literally. Return ONLY valid JSON."
            ),
            user=f"""Analyse public sentiment about "{brand_name}" based on these mentions.

Mentions:
---
{mentions_block}
---

Rules:
- Evidence MUST be literal quotes from the mentions above, not paraphrase.
- Distinguish legitimate product criticism (expensive, confusing UX) from serious controversy (lawsuits, scandals, data breaches, regulatory action).
- Set `controversy_detected: true` only for serious issues, not ordinary complaints.
- If fewer than 3 useful mentions, return `verdict: "unclear"`.
- Ignore mentions that are clearly NOT about "{brand_name}" (scraping false positives).

Return JSON with this exact structure:
{{
    "sentiment_score": 0-100,
    "verdict": "positive" | "mixed" | "negative" | "unclear",
    "overall_tone": "one sentence describing how people talk about the brand",
    "positive_themes": ["recurring positive themes"],
    "negative_themes": ["recurring negative themes or criticisms"],
    "evidence": [
        {{"quote": "literal quote from a mention", "source_url": "the url", "signal": "positive" | "negative" | "neutral"}}
    ],
    "controversy_detected": true | false,
    "controversy_details": "concrete description if true, null if false",
    "reasoning": "1-2 sentences"
}}"""
        )

    def analyze_momentum(self, mentions: list[dict], brand_name: str) -> dict:
        """
        Is the brand actively building or drifting into maintenance?

        Reads third-party mentions (last ~6 months recommended) and returns a
        structured verdict with literal quotes as evidence.

        mentions: list of dicts with keys {text, url, published_date}.
        Returns JSON-shaped dict: {momentum_score, verdict, evidence[], reasoning}.
        """
        # REVIEW: método nuevo añadido al LLMAnalyzer para soportar la feature
        # `momentum` de vitalidad. Sigue el patrón de los otros `analyze_*`.
        if not mentions:
            return {}

        lines = []
        for i, m in enumerate(mentions[:15], start=1):
            text = (m.get("text") or "")[:400].replace("\n", " ").strip()
            url = m.get("url") or ""
            date = m.get("published_date") or "unknown"
            if not text:
                continue
            lines.append(f"[{i}] ({date}) {url}\n{text}")
        mentions_block = "\n---\n".join(lines)

        if not mentions_block:
            return {}

        return self._call_json(
            system=(
                "You are a brand momentum analyst. You read recent third-party "
                "mentions and decide whether a brand is actively building, merely "
                "maintaining, or declining. You quote sources literally. Return "
                "ONLY valid JSON."
            ),
            user=f"""Assess the momentum of the brand "{brand_name}" based on these recent mentions.

Mentions:
---
{mentions_block}
---

Rules:
- Look for signals of active construction (new launches, key hires, expansion,
  strategic partnerships, significant investment) vs signals of maintenance or
  decline (media silence, layoffs, customer loss, unanswered controversies).
- Evidence MUST be literal quotes pulled from the mentions above, not paraphrase.
- If evidence is ambiguous or insufficient, return verdict "unclear" with a low score.
- Ignore mentions that are clearly NOT about "{brand_name}" (scraping false positives).

Return JSON with this exact structure:
{{
    "momentum_score": 0-100,
    "verdict": "building" | "maintaining" | "declining" | "unclear",
    "evidence": [
        {{"quote": "literal quote from a mention", "source_url": "the url", "signal": "positive" | "negative" | "neutral"}}
    ],
    "reasoning": "1-2 sentences explaining the verdict"
}}"""
        )
