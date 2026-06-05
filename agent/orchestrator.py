import logging
from pydantic import BaseModel
from agent.tools.scraper import scrape
from agent.tools.extractor import extract
from agent.tools.screenshot import take_screenshot
from agent.tools.navigator import navigate
from agent.tools.memory import Memory
from config.loader import load_settings
import sys

sys.setrecursionlimit(100)

logger = logging.getLogger(__name__)

MAX_STEPS = 10


class InvestigationPlan(BaseModel):
    tool: str        # scrape | extract | screenshot | navigate | finish
    args: dict
    reason: str


class OrchestratorResult(BaseModel):
    url: str
    success: bool
    memory_summary: str
    screenshots: list[str]
    step_count: int
    error: str | None = None


PLAN_PROMPT = """
You are an expert dark pattern investigator. You are investigating: {url}

Investigation so far:
{summary}

Available tools:
- scrape: collect raw HTML, forms, buttons, prices from a URL. args: {{"url": "..."}}
- extract: run LLM extraction on visible text for dark pattern signals. args: {{"text": "..."}}
- screenshot: take a full page screenshot. args: {{"url": "..."}}
- navigate: interact with page. args: {{"url": "...", "action": "click|scroll|goto", "target": "..."}}
- finish: stop investigation and produce report. args: {{}}

Rules:
- Always scrape and screenshot first
- Then extract signals from scraped text
- Navigate to interesting pages (checkout, pricing, subscription, cookie settings)
- finish when you have enough evidence or reached the step limit
- Return ONLY a JSON object: {{"tool": "...", "args": {{...}}, "reason": "..."}}

What is your next step?
"""


def _call_planner(url: str, summary: str, config: dict) -> InvestigationPlan | None:
    import json
    import ollama

    prompt = PLAN_PROMPT.format(url=url, summary=summary)

    try:
        if config["backend"] == "ollama":
            response = ollama.chat(
                model=config["ollama_model"],
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0}
            )
            raw = response["message"]["content"].strip()

            # strip markdown fences
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data = json.loads(raw.strip())
            return InvestigationPlan(**data)

    except Exception as e:
        logger.warning(f"Planner failed: {e}")
        return None


def _execute(plan: InvestigationPlan, memory: Memory) -> bool:
    """Executes a plan step. Returns False if agent should stop."""

    # hard safety limit
    if memory.state.step_count >= MAX_STEPS:
        logger.warning("Hard step limit reached — stopping")
        return False

    tool = plan.tool
    args = plan.args
    logger.info(f"Executing: {tool} — {plan.reason}")

    if tool == "finish":
        return False

    elif tool == "scrape":
        result = scrape(args.get("url", memory.state.url))
        memory.add_scrape(result)

    elif tool == "extract":
        text = args.get("text", "")
        if not text:
            # use last scraped text from findings
            for f in reversed(memory.state.findings):
                if f.tool == "scraper":
                    text = f.evidence
                    break
        result = extract(text)
        memory.add_extraction(result)

    elif tool == "screenshot":
        result = take_screenshot(args.get("url", memory.state.url))
        memory.add_screenshot(result)

    elif tool == "navigate":
        result = navigate(
            url=args.get("url", memory.state.url),
            action=args.get("action", "scroll"),
            target=args.get("target", "500")
        )
        memory.add_navigation(result)

        # only scrape new pages — avoid revisiting
        if (result.success and
            result.url_after != result.url_before and
            result.url_after not in memory.state.visited_urls):
            scrape_result = scrape(result.url_after)
            memory.add_scrape(scrape_result)
            extract_result = extract(scrape_result.visible_text)
            memory.add_extraction(extract_result)

    else:
        logger.warning(f"Unknown tool: {tool}")
        memory.add_custom(f"Unknown tool requested: {tool}")

    return True


def investigate(url: str) -> OrchestratorResult:
    settings = load_settings()
    extractor_config = settings["llm"]["extractor"]

    logger.info(f"Starting investigation of {url}")
    memory = Memory(url)

    # — step 1: always scrape and screenshot first —
    logger.info("Step 1: initial scrape")
    scrape_result = scrape(url)
    memory.add_scrape(scrape_result)

    logger.info("Step 2: initial extraction")
    if scrape_result.scrape_success:
        extract_result = extract(scrape_result.visible_text)
        memory.add_extraction(extract_result)

    logger.info("Step 3: initial screenshot")
    screenshot_result = take_screenshot(url)
    memory.add_screenshot(screenshot_result)

    # — agentic loop —
    for step in range(MAX_STEPS):
        logger.info(f"Agent loop step {step + 1}/{MAX_STEPS}")

        if memory.has_enough_evidence():
            logger.info("Agent decided: enough evidence collected")
            memory.add_custom("Sufficient evidence collected — stopping investigation")
            break

        summary = memory.get_summary()
        plan = _call_planner(url, summary, extractor_config)

        if plan is None:
            logger.warning("Planner returned no plan — stopping")
            memory.add_custom("Planner failed — stopping investigation")
            break

        logger.info(f"Plan: {plan.tool} — {plan.reason}")
        memory.add_custom(f"Plan: {plan.tool} — {plan.reason}")

        should_continue = _execute(plan, memory)
        if not should_continue:
            logger.info("Agent chose to finish")
            break

    logger.info(f"Investigation complete — {memory.state.step_count} steps")

    return OrchestratorResult(
        url=url,
        success=True,
        memory_summary=memory.get_summary(),
        screenshots=memory.state.screenshots,
        step_count=memory.state.step_count,
        error=None
    )