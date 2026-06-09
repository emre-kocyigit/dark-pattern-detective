# Contributing to Dark Pattern Detective

Thank you for your interest in contributing. This document covers setup, project structure, conventions, and the current development roadmap.

---

## Getting started

**Requirements:** Python 3.11+, [Ollama](https://ollama.com) (for local LLM backend)

```bash
git clone https://github.com/emre-kocyigit/dark-pattern-detective.git
cd dark-pattern-detective
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -e .
playwright install chromium
```

Pull the required Ollama models:

```bash
ollama pull llama3.2        # extractor
ollama pull llama3.1:8b     # analyst
ollama pull llava           # vision (optional)
```

Copy `.env.example` to `.env` and configure your backend:

```
LLM_BACKEND=ollama
EXTRACTOR_OLLAMA_MODEL=llama3.2:3b
ANALYST_OLLAMA_MODEL=llama3.1:8b
```

---

## Project structure

```
dark-pattern-detective/
├── agent/
│   ├── orchestrator.py     # main agent loop
│   ├── prompts.py          # all LLM prompts
│   └── tools/
│       ├── scraper.py      # HTML/form/price/consent extraction
│       ├── extractor.py    # LLM + rule-based dark pattern extraction
│       ├── navigator.py    # Playwright browser interactions
│       ├── screenshot.py   # full-page capture
│       └── memory.py       # evidence accumulation across steps
├── llm/
│   └── analyst.py          # multimodal analyst LLM
├── report/
│   └── formatter.py        # terminal table + JSON output
├── config/
│   ├── settings.yaml       # all tuneable settings
│   └── patterns.yaml       # fallback dark pattern definitions
├── tests/                  # pytest test suite (43 tests)
└── cli.py                  # Typer CLI entry point
```

---

## Running tests

```bash
pytest tests/ -v --tb=short
```

All tests should pass before opening a PR. Tests are unit-level and use mocks — no live network calls or running Ollama instance required.

---

## Conventions

- **Python 3.11+**, type hints throughout.
- **No hardcoded values** — all settings go in `config/settings.yaml`, all prompts go in `agent/prompts.py`.
- **No new patterns in code** — dark pattern definitions belong in `config/patterns.yaml`.
- Keep functions small and single-purpose.
- Do not add comments that explain what the code does — only add one when the *why* is non-obvious.

---

## LLM backends

| Backend | Extractor | Analyst | Notes |
|---|---|---|---|
| Ollama (default) | llama3.2:3b | llama3.1:8b | Local, private, free |
| OpenAI | gpt-4o-mini | gpt-4o | Best detection quality |
| Anthropic | claude-haiku-4-5 | claude-opus-4-6 | Coming soon |

---

## Roadmap

| Priority | Area | Description |
|---|---|---|
| 🔴 High | **Streamlit UI** | Web interface: URL input, live agent log, results table, screenshot viewer |
| 🟡 Medium | Docker + HF Spaces | Containerise and deploy to Hugging Face Spaces |
| 🟡 Medium | Multi-agent architecture | Separate scraper agent and analyst agent |
| 🟢 Low | Language support | Extend beyond English and Turkish |
| 🟢 Low | Benchmarking | Evaluate against the DECEPTICON dataset |

If you are picking up the **Streamlit UI**, the entry point should live at `ui/app.py` and import from `agent/`, `llm/`, and `report/` — do not duplicate logic.

---

## Submitting changes

1. Fork the repository and create a branch: `git checkout -b feat/your-feature`
2. Make your changes and ensure all tests pass.
3. Open a pull request against `main` with a clear description of what and why.

---

## Author

**Emre KOCYIGIT** — [LinkedIn](https://linkedin.com/in/kocyigitemre) · [Google Scholar](https://scholar.google.com/citations?user=3rwgb7YAAAAJ)
