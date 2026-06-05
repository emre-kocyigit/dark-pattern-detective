# Dark Pattern Detective 🕵️

An autonomous agent that investigates websites for deceptive UI patterns — give it a URL, it scrapes, navigates, screenshots, and analyses the page using a multimodal LLM grounded in peer-reviewed research.

```bash
darkpattern investigate --url https://www.booking.com --output both
```

```
✓ Done in 104s — 4 steps · 1 screenshots · 4 patterns found

⚠️ Overall risk: HIGH

Multiple instances of dark patterns found on booking.com, including drip
pricing, reference pricing, sneak into basket, and forced registration.
⚖️  GDPR concerns detected

┌─────────────────────────┬───────┬──────────────────────┬──────────┬──────┐
│ Pattern                 │ Level │ Strategy             │ Severity │ GDPR │
├─────────────────────────┼───────┼──────────────────────┼──────────┼──────┤
│ Drip Pricing            │ low   │ 🎭 Sneaking          │ HIGH     │  ⚠️  │
│ Reference Pricing       │ low   │ 🎭 Sneaking          │ HIGH     │  ⚠️  │
│ Sneak into Basket       │ low   │ 🎭 Sneaking          │ MEDIUM   │  ⚠️  │
│ Forced Registration     │ meso  │ ⛓️  Forced Action    │ HIGH     │  ⚠️  │
└─────────────────────────┴───────┴──────────────────────┴──────────┴──────┘
```

---

## What makes this different

Most dark pattern tools are rule-based scanners or single-page classifiers. Dark Pattern Detective is an **autonomous agent** that investigates the way a human auditor would:

- **Scrapes** HTML, forms, buttons, prices, consent elements
- **Navigates** through checkout flows, cookie banners, subscription pages
- **Screenshots** the page for visual evidence
- **Extracts** semantic signals using a hybrid LLM + rule-based approach
- **Analyses** all accumulated evidence using a multimodal LLM

The detection taxonomy is grounded in the CHI 2024 dark patterns ontology (Gray, Santos, Bielova & Mildner) — 5 high-level strategies, 25 meso-level patterns, 35 low-level patterns — with legal references to GDPR, DSA, DMA, and EU Consumer Protection law.

---

## Architecture

<pre>
URL input
    │
    ▼
Agent Orchestrator (LangChain-style loop)
    │
    ├── scraper      → HTML, forms, buttons, prices, consent elements
    ├── extractor    → LLM-primary + YAML fallback, EN + TR language support
    ├── screenshot   → full-page Playwright capture
    └── navigator    → click, scroll, goto, hover interactions
    │
    ▼
Memory (accumulates evidence across all steps)
    │
    ▼
Analyst LLM (multimodal — text + screenshots)
    │
    ▼
Structured report (terminal + JSON)
</pre>

---

## Installation

**Requirements:** Python 3.11+, [Ollama](https://ollama.com) (for local backend)

```bash
git clone https://github.com/emre-kocyigit/dark-pattern-detective.git
cd dark-pattern-detective
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -e .
playwright install chromium
```

Pull the required models:

```bash
ollama pull llama3.2        # extractor (text)
ollama pull llama3.1:8b     # analyst (reasoning)
ollama pull llava           # analyst vision (optional)
```

Configure your backend in `.env`:

```
LLM_BACKEND=ollama
EXTRACTOR_OLLAMA_MODEL=llama3.2:3b
ANALYST_OLLAMA_MODEL=llama3.1:8b

# For OpenAI backend:
# LLM_BACKEND=openai
# OPENAI_API_KEY=your_key
```

---

## Usage

**Basic investigation:**
```bash
darkpattern investigate --url https://www.booking.com
```

**Save JSON report:**
```bash
darkpattern investigate --url https://www.booking.com --output both
```

**Use OpenAI backend:**
```bash
darkpattern investigate --url https://www.booking.com --backend openai
```

**Verbose mode (see agent reasoning):**
```bash
darkpattern investigate --url https://www.booking.com --verbose
```

**JSON report structure:**
```json
{
  "url": "https://www.booking.com",
  "overall_risk": "HIGH",
  "gdpr_concerns": true,
  "pattern_count": 4,
  "dark_patterns_found": [
    {
      "pattern": "Drip Pricing",
      "level": "low",
      "high_level_strategy": "Sneaking",
      "severity": "HIGH",
      "evidence": "$449 shown initially, $262 at checkout",
      "location": "pricing section",
      "gdpr_risk": true,
      "legal_reference": "Consumer Protection Law",
      "recommendation": "Display full price upfront"
    }
  ]
}
```

---

## Dark pattern taxonomy

Detection is grounded in the CHI 2024 ontology with three levels of hierarchy:

| High-level strategy | Example meso patterns | Example low-level patterns |
|---|---|---|
| Sneaking | Hiding Information, Bait and Switch | Drip Pricing, Sneak into Basket, Disguised Ads |
| Obstruction | Roach Motel, Creating Barriers | Immortal Accounts, Privacy Maze, Dead Ends |
| Interface Interference | Bad Defaults, Trick Questions | False Hierarchy, Confirmshaming, Bundling |
| Forced Action | Nagging, Forced Continuity | Privacy Zuckering, Auto-Play, Forced Registration |
| Social Engineering | Urgency, Scarcity Claims | Countdown Timer, Low Stock Message, Confirmshaming |

---

## Configuration

All settings in `config/settings.yaml` — no hardcoded values:

```yaml
llm:
  extractor:
    backend: ollama        # ollama | openai | anthropic
    ollama_model: llama3.2:3b
  analyst:
    backend: ollama
    ollama_model: llama3.1:8b

scraper:
  timeout: 30000
  max_visible_text: 8000

extraction:
  languages: [en, tr]      # English and Turkish supported
  use_llm: true
  fallback_on_error: true
```

Fallback patterns in `config/patterns.yaml` — editable without touching code.

---

## LLM backends

| Backend | Extractor model | Analyst model | Notes |
|---|---|---|---|
| Ollama (default) | llama3.2:3b | llama3.1:8b | Local, private, free |
| OpenAI | gpt-4o-mini | gpt-4o | Best results |
| Anthropic | claude-haiku-4-5 | claude-opus-4-6 | Coming soon |

GPT-4o gives significantly better detection results than local models. Local models are recommended for privacy-sensitive investigations.

---

## Tests

```bash
pytest tests/ -v --tb=no
```

43 tests across all components: scraper, extractor, screenshot, navigator, memory, orchestrator, analyst, formatter.

---


## Research background

This tool is an independent engineering project inspired by research on multimodal dark pattern detection. The agentic architecture and detection approach were designed and built from scratch.

The concept of multimodal LLM-based dark pattern detection is inspired by:

- Kocyigit, E. et al. (2025). DeceptiLens: an Approach supporting Transparency in Deceptive Pattern Detection based on a Multimodal Large Language Model. **ACM FAccT 2025.**

Detection taxonomy based on:

- Gray, Santos, Bielova & Mildner (2024). An Ontology of Dark Patterns Knowledge. **CHI 2024.**

---

## Roadmap

- [ ] Streamlit web UI
- [ ] Docker + Hugging Face Spaces deployment
- [ ] Multi-agent architecture (scraper agent + analyst agent)
- [ ] Extended language support
- [ ] Benchmark against DECEPTICON dataset

---

## Author

**Emre KOCYIGIT** — Data Scientist & AI/ML Engineer & Applied AI Researcher  
[LinkedIn](https://linkedin.com/in/kocyigitemre) · [Medium](https://medium.com/@kocyigit.emre.30) · [Google Scholar](https://scholar.google.com/citations?user=3rwgb7YAAAAJ&hl=en&oi=ao)