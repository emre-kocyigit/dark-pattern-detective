import logging
import json
from pydantic import BaseModel
from config.loader import get_extractor_config, get_patterns_flat, load_settings
import ollama
from openai import OpenAI

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are a dark pattern detection expert analyzing webpage content.
Supported languages: English and Turkish.

Analyze the text below and extract manipulation signals.
Return ONLY a valid JSON object with exactly these fields — no explanation, no markdown:

{{
  "urgency_texts": [],
  "subscription_keywords": [],
  "consent_accept": [],
  "consent_reject": [],
  "dark_pattern_hints": [],
  "language_detected": "en|tr|mixed"
}}

Field definitions:
- urgency_texts: phrases creating false urgency or scarcity ("only 2 left", "offer ends soon", "son 2 ürün")
- subscription_keywords: subscription, auto-renewal, billing language ("auto-renews monthly", "otomatik yenileme")
- consent_accept: accept/agree button texts found ("accept all", "tümünü kabul et")
- consent_reject: reject/decline button texts found ("reject all", "reddet")
- dark_pattern_hints: any other suspicious or manipulative language not covered above
- language_detected: dominant language of the page

Rules:
- Extract exact phrases from the text, do not invent
- Be inclusive — if unsure, include it
- Empty list is fine if nothing found

Webpage text:
{text}
"""


class ExtractionResult(BaseModel):
    urgency_texts: list[str]
    subscription_keywords: list[str]
    consent_accept: list[str]
    consent_reject: list[str]
    dark_pattern_hints: list[str]
    extraction_method: str  # "llm" | "fallback" | "hybrid"
    language_detected: str


def _parse_llm_response(raw: str) -> dict | None:
    try:
        raw = raw.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        brace_idx = raw.find("{")
        if brace_idx > 0:
            raw = raw[brace_idx:]

        last_brace = raw.rfind("}")
        if last_brace != -1:
            raw = raw[:last_brace + 1]

        return json.loads(raw.strip())

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e} — raw: {raw[:200]}")
        return None


def _validate(result: dict) -> bool:
    required = [
        "urgency_texts", "subscription_keywords",
        "consent_accept", "consent_reject",
        "dark_pattern_hints", "language_detected"
    ]
    return (
        all(k in result for k in required) and
        all(isinstance(result[k], list) for k in required[:-1]) and
        isinstance(result["language_detected"], str)
    )


def _call_ollama(text: str, config: dict) -> dict | None:
    try:
        response = ollama.chat(
            model=config["ollama_model"],
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(text=text[:6000])
            }],
            options={"temperature": config["temperature"]}
        )
        raw = response["message"]["content"]
        return _parse_llm_response(raw)
    except Exception as e:
        logger.warning(f"Ollama call failed: {e}")
        return None


def _call_openai(text: str, config: dict, api_key: str) -> dict | None:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=config["openai_model"],
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(text=text[:6000])
            }],
            temperature=config["temperature"],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"OpenAI call failed: {e}")
        return None


def _fallback_extract(text: str, languages: list[str]) -> dict:
    """Rule-based fallback using YAML patterns."""
    logger.info("Using rule-based fallback extraction")
    text_lower = text.lower()

    def match(category: str) -> list[str]:
        patterns = get_patterns_flat(category, languages)
        return [p for p in patterns if p.lower() in text_lower]

    return {
        "urgency_texts": match("urgency"),
        "subscription_keywords": match("subscription"),
        "consent_accept": match("consent_accept"),
        "consent_reject": match("consent_reject"),
        "dark_pattern_hints": [],
        "language_detected": "unknown"
    }


def _merge(llm: dict, fallback: dict) -> dict:
    """Merges LLM and fallback results — LLM is primary, fallback fills gaps."""
    def combine(key: str) -> list[str]:
        return list(set(llm.get(key, []) + fallback.get(key, [])))

    return {
        "urgency_texts": combine("urgency_texts"),
        "subscription_keywords": combine("subscription_keywords"),
        "consent_accept": combine("consent_accept"),
        "consent_reject": combine("consent_reject"),
        "dark_pattern_hints": llm.get("dark_pattern_hints", []),
        "language_detected": llm.get("language_detected", "unknown")
    }


def extract(visible_text: str) -> ExtractionResult:
    config = get_extractor_config()
    settings = load_settings()
    languages = settings["extraction"]["languages"]
    use_llm = settings["extraction"]["use_llm"]
    fallback_on_error = settings["extraction"]["fallback_on_error"]

    fallback = _fallback_extract(visible_text, languages)
    llm_result = None
    method = "fallback"

    if use_llm:
        backend = config["backend"]
        logger.info(f"Running LLM extraction via {backend} ({config.get(f'{backend}_model', '')})")

        if backend == "ollama":
            llm_result = _call_ollama(visible_text, config)
        elif backend == "openai":
            api_key = settings["llm"].get("openai_api_key", "")
            if api_key:
                llm_result = _call_openai(visible_text, config, api_key)
            else:
                logger.warning("OpenAI key not set — falling back")

        if llm_result and _validate(llm_result):
            logger.info("LLM extraction succeeded")
            merged = _merge(llm_result, fallback)
            method = "hybrid"
        else:
            logger.warning("LLM result invalid — using fallback only")
            if not fallback_on_error:
                raise RuntimeError("LLM extraction failed and fallback is disabled")
            merged = fallback
            method = "fallback"
    else:
        merged = fallback
        method = "fallback"

    return ExtractionResult(
        urgency_texts=merged["urgency_texts"][:10],
        subscription_keywords=merged["subscription_keywords"][:10],
        consent_accept=merged["consent_accept"][:10],
        consent_reject=merged["consent_reject"][:10],
        dark_pattern_hints=merged["dark_pattern_hints"][:10],
        extraction_method=method,
        language_detected=merged["language_detected"]
    )