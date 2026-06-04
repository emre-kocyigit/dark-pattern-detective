import logging
import json
from pydantic import BaseModel
from agent.prompts import DARK_PATTERN_TAXONOMY
from config.loader import get_analyst_config, load_settings

logger = logging.getLogger(__name__)


class DarkPatternFinding(BaseModel):
    pattern: str
    level: str                    # "low" | "meso"
    high_level_strategy: str
    severity: str                 # "HIGH" | "MEDIUM" | "LOW"
    evidence: str
    location: str
    gdpr_risk: bool
    legal_reference: str | None
    recommendation: str


class AnalysisReport(BaseModel):
    dark_patterns_found: list[DarkPatternFinding]
    overall_risk: str             # "HIGH" | "MEDIUM" | "LOW" | "CLEAN"
    overall_summary: str
    gdpr_concerns: bool
    pattern_count: int
    language_detected: str
    ontology_reference: str
    analysis_success: bool
    analysis_error: str | None = None


def _empty_report(error: str) -> AnalysisReport:
    return AnalysisReport(
        dark_patterns_found=[],
        overall_risk="UNKNOWN",
        overall_summary="Analysis failed.",
        gdpr_concerns=False,
        pattern_count=0,
        language_detected="unknown",
        ontology_reference="Gray, Santos, Bielova & Mildner (2024). CHI 2024.",
        analysis_success=False,
        analysis_error=error
    )


def _parse_response(raw: str) -> dict | None:
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e} — raw preview: {raw[:300]}")
        return None


def _validate(data: dict) -> bool:
    required = [
        "dark_patterns_found", "overall_risk", "overall_summary",
        "gdpr_concerns", "pattern_count", "language_detected"
    ]
    return all(k in data for k in required)


def _call_ollama(prompt: str, config: dict) -> dict | None:
    try:
        import ollama

        # check if model supports vision
        model = config["ollama_model"]
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": config["temperature"]}
        )
        raw = response["message"]["content"]
        return _parse_response(raw)
    except Exception as e:
        logger.warning(f"Ollama analyst call failed: {e}")
        return None


def _call_ollama_vision(
    prompt: str,
    screenshot_paths: list[str],
    config: dict
) -> dict | None:
    try:
        import ollama
        from pathlib import Path
        import base64

        images = []
        for path in screenshot_paths[:3]:  # max 3 screenshots
            p = Path(path)
            if p.exists():
                with open(p, "rb") as f:
                    images.append(base64.b64encode(f.read()).decode())

        if images:
            response = ollama.chat(
                model=config["ollama_model"],
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": images
                }],
                options={"temperature": config["temperature"]}
            )
        else:
            # no valid screenshots — text only
            logger.warning("No valid screenshots found — falling back to text-only analysis")
            response = ollama.chat(
                model=config["ollama_model"],
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": config["temperature"]}
            )

        raw = response["message"]["content"]
        return _parse_response(raw)

    except Exception as e:
        logger.warning(f"Ollama vision analyst call failed: {e}")
        return None


def _call_openai(
    prompt: str,
    screenshot_paths: list[str],
    config: dict,
    api_key: str
) -> dict | None:
    try:
        from openai import OpenAI
        from pathlib import Path
        import base64

        client = OpenAI(api_key=api_key)
        content = [{"type": "text", "text": prompt}]

        for path in screenshot_paths[:3]:
            p = Path(path)
            if p.exists():
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "high"
                    }
                })

        response = client.chat.completions.create(
            model=config["openai_model"],
            messages=[{"role": "user", "content": content}],
            temperature=config["temperature"],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.warning(f"OpenAI analyst call failed: {e}")
        return None


def _build_prompt(evidence_summary: str, screenshot_count: int) -> str:
    return DARK_PATTERN_TAXONOMY.format(
        evidence_summary=evidence_summary,
        screenshot_count=screenshot_count
    )


def analyze(
    evidence_summary: str,
    screenshot_paths: list[str]
) -> AnalysisReport:
    config = get_analyst_config()
    settings = load_settings()
    backend = config["backend"]
    screenshot_count = len(screenshot_paths)

    logger.info(
        f"Running analysis via {backend} ({config.get(f'{backend}_model', '')}) "
        f"| screenshots: {screenshot_count}"
    )

    prompt = _build_prompt(evidence_summary, screenshot_count)
    result = None

    if backend == "ollama":
        # try vision first, fall back to text-only
        if screenshot_paths:
            result = _call_ollama_vision(prompt, screenshot_paths, config)
        if result is None:
            result = _call_ollama(prompt, config)

    elif backend == "openai":
        api_key = settings["llm"].get("openai_api_key", "")
        if api_key:
            result = _call_openai(prompt, screenshot_paths, config, api_key)
        else:
            logger.warning("OpenAI key not set")

    if result is None:
        logger.error("All analyst backends failed")
        return _empty_report("All backends failed")

    if not _validate(result):
        logger.error(f"Invalid analyst response structure: {result}")
        return _empty_report("Invalid response structure from LLM")

    try:
        findings = [
            DarkPatternFinding(**f)
            for f in result.get("dark_patterns_found", [])
        ]

        return AnalysisReport(
            dark_patterns_found=findings,
            overall_risk=result.get("overall_risk", "UNKNOWN"),
            overall_summary=result.get("overall_summary", ""),
            gdpr_concerns=result.get("gdpr_concerns", False),
            pattern_count=result.get("pattern_count", len(findings)),
            language_detected=result.get("language_detected", "unknown"),
            ontology_reference=result.get(
                "ontology_reference",
                "Gray, Santos, Bielova & Mildner (2024). CHI 2024."
            ),
            analysis_success=True,
            analysis_error=None
        )

    except Exception as e:
        logger.error(f"Failed to build AnalysisReport: {e}")
        return _empty_report(f"Report construction failed: {e}")