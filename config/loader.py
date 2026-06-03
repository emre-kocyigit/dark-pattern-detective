from dotenv import load_dotenv
load_dotenv()

import os
import yaml
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml") as f:
        settings = yaml.safe_load(f)

    # global backend override
    global_backend = os.getenv("LLM_BACKEND")

    # extractor overrides
    ext = settings["llm"]["extractor"]
    ext["backend"] = os.getenv("EXTRACTOR_BACKEND") or global_backend or ext["backend"]
    ext["ollama_model"] = os.getenv("EXTRACTOR_OLLAMA_MODEL") or ext["ollama_model"]

    # analyst overrides
    ana = settings["llm"]["analyst"]
    ana["backend"] = os.getenv("ANALYST_BACKEND") or global_backend or ana["backend"]
    ana["ollama_model"] = os.getenv("ANALYST_OLLAMA_MODEL") or ana["ollama_model"]

    # api keys
    settings["llm"]["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
    settings["llm"]["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY", "")

    return settings


@lru_cache(maxsize=1)
def load_patterns() -> dict:
    with open(CONFIG_DIR / "patterns.yaml") as f:
        return yaml.safe_load(f)


def get_extractor_config() -> dict:
    return load_settings()["llm"]["extractor"]


def get_analyst_config() -> dict:
    return load_settings()["llm"]["analyst"]


def get_patterns_flat(category: str, languages: list[str]) -> list[str]:
    patterns = load_patterns()
    result = []
    for lang in languages:
        result.extend(patterns.get(category, {}).get(lang, []))
    return result