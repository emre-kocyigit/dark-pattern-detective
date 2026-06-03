import logging
from datetime import datetime
from pydantic import BaseModel
from agent.tools.scraper import ScrapedPage
from agent.tools.extractor import ExtractionResult
from agent.tools.screenshot import Screenshot
from agent.tools.navigator import NavigationResult

logger = logging.getLogger(__name__)


class Finding(BaseModel):
    step: int
    timestamp: str
    tool: str
    summary: str
    evidence: str


class InvestigationMemory(BaseModel):
    url: str
    started_at: str
    findings: list[Finding] = []
    screenshots: list[str] = []
    visited_urls: list[str] = []
    step_count: int = 0

    # accumulated signals across all steps
    all_urgency_texts: list[str] = []
    all_subscription_keywords: list[str] = []
    all_consent_accept: list[str] = []
    all_consent_reject: list[str] = []
    all_dark_pattern_hints: list[str] = []
    all_prices: list[str] = []
    all_preselected_checkboxes: list[dict] = []
    all_hidden_inputs: list[dict] = []
    popup_detected: bool = False
    reject_button_missing: bool = False


class Memory:
    def __init__(self, url: str):
        self.state = InvestigationMemory(
            url=url,
            started_at=datetime.now().isoformat()
        )
        logger.info(f"Memory initialized for {url}")

    def _next_step(self) -> int:
        self.state.step_count += 1
        return self.state.step_count

    def _add_finding(self, tool: str, summary: str, evidence: str):
        self.state.findings.append(Finding(
            step=self._next_step(),
            timestamp=datetime.now().isoformat(),
            tool=tool,
            summary=summary,
            evidence=evidence[:500]
        ))

    def add_scrape(self, result: ScrapedPage):
        if not result.scrape_success:
            self._add_finding(
                tool="scraper",
                summary=f"Scrape failed: {result.scrape_error}",
                evidence=""
            )
            return

        # accumulate structural signals
        self.state.all_prices.extend(result.prices)
        self.state.all_preselected_checkboxes.extend(result.preselected_checkboxes)
        self.state.all_hidden_inputs.extend(result.hidden_inputs)

        if result.popup_detected:
            self.state.popup_detected = True

        if result.url not in self.state.visited_urls:
            self.state.visited_urls.append(result.url)

        summary_parts = []
        if result.preselected_checkboxes:
            summary_parts.append(f"{len(result.preselected_checkboxes)} preselected checkboxes")
        if result.popup_detected:
            summary_parts.append("popup detected")
        if result.prices:
            summary_parts.append(f"prices found: {result.prices[:3]}")
        if result.small_print:
            summary_parts.append(f"{len(result.small_print)} small print elements")

        self._add_finding(
            tool="scraper",
            summary=f"Scraped {result.url} — " + (", ".join(summary_parts) or "no red flags"),
            evidence=result.visible_text[:500]
        )

    def add_extraction(self, result: ExtractionResult):
        # accumulate semantic signals
        self.state.all_urgency_texts.extend(result.urgency_texts)
        self.state.all_subscription_keywords.extend(result.subscription_keywords)
        self.state.all_consent_accept.extend(result.consent_accept)
        self.state.all_consent_reject.extend(result.consent_reject)
        self.state.all_dark_pattern_hints.extend(result.dark_pattern_hints)

        if result.consent_accept and not result.consent_reject:
            self.state.reject_button_missing = True

        summary_parts = []
        if result.urgency_texts:
            summary_parts.append(f"urgency: {result.urgency_texts[:2]}")
        if result.subscription_keywords:
            summary_parts.append(f"subscription: {result.subscription_keywords[:2]}")
        if result.dark_pattern_hints:
            summary_parts.append(f"hints: {result.dark_pattern_hints[:2]}")

        self._add_finding(
            tool="extractor",
            summary=f"Extraction ({result.extraction_method}) — " + (
                ", ".join(summary_parts) or "no signals found"
            ),
            evidence=str(result.model_dump())[:500]
        )

    def add_screenshot(self, result: Screenshot):
        if result.success:
            self.state.screenshots.append(result.path)
            self._add_finding(
                tool="screenshot",
                summary=f"Screenshot saved — {result.width}x{result.height}px",
                evidence=result.path
            )
        else:
            self._add_finding(
                tool="screenshot",
                summary=f"Screenshot failed: {result.error}",
                evidence=""
            )

    def add_navigation(self, result: NavigationResult):
        if result.url_after not in self.state.visited_urls:
            self.state.visited_urls.append(result.url_after)

        self._add_finding(
            tool="navigator",
            summary=f"{result.action} on {result.action_target!r} — "
                    f"landed on {result.url_after}",
            evidence=result.visible_text_after[:500]
        )

    def add_custom(self, summary: str, evidence: str = ""):
        """For agent to log its own reasoning steps."""
        self._add_finding(
            tool="agent",
            summary=summary,
            evidence=evidence
        )

    def get_summary(self) -> str:
        """Returns a text summary of all findings for the analyst LLM."""
        lines = [
            f"Investigation of: {self.state.url}",
            f"Steps taken: {self.state.step_count}",
            f"Pages visited: {self.state.visited_urls}",
            f"Screenshots taken: {len(self.state.screenshots)}",
            "",
            "=== Accumulated signals ===",
            f"Urgency texts: {list(set(self.state.all_urgency_texts))}",
            f"Subscription keywords: {list(set(self.state.all_subscription_keywords))}",
            f"Prices found: {list(set(self.state.all_prices))}",
            f"Preselected checkboxes: {self.state.all_preselected_checkboxes}",
            f"Hidden inputs: {self.state.all_hidden_inputs}",
            f"Consent accept buttons: {list(set(self.state.all_consent_accept))}",
            f"Consent reject buttons: {list(set(self.state.all_consent_reject))}",
            f"Reject button missing: {self.state.reject_button_missing}",
            f"Popup detected: {self.state.popup_detected}",
            f"Dark pattern hints: {list(set(self.state.all_dark_pattern_hints))}",
            "",
            "=== Investigation steps ===",
        ]
        for f in self.state.findings:
            lines.append(f"[{f.step}] {f.tool.upper()}: {f.summary}")

        return "\n".join(lines)

    def has_enough_evidence(self) -> bool:
        """Tells the agent when it has enough to produce a report."""
        has_screenshots = len(self.state.screenshots) > 0
        has_signals = any([
            self.state.all_urgency_texts,
            self.state.all_subscription_keywords,
            self.state.all_dark_pattern_hints,
            self.state.all_preselected_checkboxes,
            self.state.popup_detected,
            self.state.reject_button_missing,
        ])
        has_visited = len(self.state.visited_urls) > 0
        return has_screenshots and has_visited and self.state.step_count >= 3