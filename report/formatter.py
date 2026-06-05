import json
import logging
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from llm.analyst import AnalysisReport, DarkPatternFinding

logger = logging.getLogger(__name__)
console = Console()

SEVERITY_COLORS = {
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
}

RISK_COLORS = {
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
    "CLEAN": "green",
    "UNKNOWN": "white",
}

STRATEGY_ICONS = {
    "Sneaking": "🎭",
    "Obstruction": "🚧",
    "Interface Interference": "🎨",
    "Forced Action": "⛓️",
    "Social Engineering": "🧠",
}


def _risk_panel(report: AnalysisReport, url: str) -> Panel:
    color = RISK_COLORS.get(report.overall_risk, "white")
    icon = "✅" if report.overall_risk == "CLEAN" else "⚠️"

    text = Text()
    text.append(f"{icon} Overall risk: ", style="bold")
    text.append(report.overall_risk, style=f"bold {color}")
    text.append(f"\n\n{report.overall_summary}")

    if report.gdpr_concerns:
        text.append("\n\n⚖️  GDPR concerns detected", style="bold red")

    return Panel(
        text,
        title=f"[bold]Dark Pattern Investigation Report[/bold]",
        subtitle=f"[dim]{url}[/dim]",
        border_style=color,
        padding=(1, 2)
    )


def _findings_table(findings: list[DarkPatternFinding]) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        title=f"Findings ({len(findings)} pattern{'s' if len(findings) != 1 else ''} detected)",
        expand=True
    )

    table.add_column("Pattern", style="bold", min_width=25)
    table.add_column("Level", justify="center", min_width=6)
    table.add_column("Strategy", min_width=20)
    table.add_column("Severity", justify="center", min_width=8)
    table.add_column("Location", min_width=15)
    table.add_column("GDPR", justify="center", min_width=5)

    for f in findings:
        severity_color = SEVERITY_COLORS.get(f.severity, "white")
        icon = STRATEGY_ICONS.get(f.high_level_strategy, "•")
        gdpr = "⚠️" if f.gdpr_risk else "—"

        table.add_row(
            f.pattern,
            f"[dim]{f.level}[/dim]",
            f"{icon} {f.high_level_strategy}",
            f"[{severity_color}]{f.severity}[/{severity_color}]",
            f.location[:30],
            gdpr
        )

    return table


def _finding_details(findings: list[DarkPatternFinding]):
    for i, f in enumerate(findings, 1):
        severity_color = SEVERITY_COLORS.get(f.severity, "white")
        icon = STRATEGY_ICONS.get(f.high_level_strategy, "•")

        text = Text()
        text.append(f"Pattern:    ", style="dim")
        text.append(f"{f.pattern}", style="bold")
        text.append(f"\nLevel:      ", style="dim")
        text.append(f"{f.level}")
        text.append(f"\nStrategy:   ", style="dim")
        text.append(f"{icon} {f.high_level_strategy}")
        text.append(f"\nSeverity:   ", style="dim")
        text.append(f"{f.severity}", style=f"bold {severity_color}")
        text.append(f"\nLocation:   ", style="dim")
        text.append(f.location)
        text.append(f"\nEvidence:   ", style="dim")
        text.append(f.evidence, style="italic")
        if f.legal_reference:
            text.append(f"\nLegal ref:  ", style="dim")
            text.append(f.legal_reference, style="yellow")
        text.append(f"\nFix:        ", style="dim")
        text.append(f.recommendation, style="green")

        console.print(Panel(
            text,
            title=f"[dim]Finding {i} of {len(findings)}[/dim]",
            border_style=severity_color,
            padding=(1, 2)
        ))


def _save_json(
    report: AnalysisReport,
    url: str,
    output_dir: str = "output/reports"
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_url = "".join(c if c.isalnum() else "_" for c in url)[:50]
    filename = f"{clean_url}_{timestamp}.json"
    filepath = Path(output_dir) / filename

    data = {
        "url": url,
        "timestamp": timestamp,
        "overall_risk": report.overall_risk,
        "overall_summary": report.overall_summary,
        "gdpr_concerns": report.gdpr_concerns,
        "pattern_count": report.pattern_count,
        "language_detected": report.language_detected,
        "ontology_reference": report.ontology_reference,
        "dark_patterns_found": [
            f.model_dump() for f in report.dark_patterns_found
        ]
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(filepath)


def print_report(
    report: AnalysisReport,
    url: str,
    output: str = "terminal"  # "terminal" | "json" | "both"
) -> str | None:
    """
    Renders the report to terminal and/or saves as JSON.
    Returns JSON filepath if saved, None otherwise.
    """
    json_path = None

    if output in ("terminal", "both"):
        console.print()
        console.print(_risk_panel(report, url))
        console.print()

        if report.dark_patterns_found:
            console.print(_findings_table(report.dark_patterns_found))
            console.print()
            _finding_details(report.dark_patterns_found)
        else:
            console.print(Panel(
                "[green]No dark patterns detected on this page.[/green]",
                border_style="green",
                padding=(1, 2)
            ))

        console.print()

    if output in ("json", "both"):
        json_path = _save_json(report, url)
        console.print(f"[dim]Report saved to: {json_path}[/dim]")

    return json_path