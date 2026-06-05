import logging
import sys
import time
import typer
from typing import Annotated
from rich.console import Console
from agent.orchestrator import investigate as run_investigation
from llm.analyst import analyze
from report.formatter import print_report
from config.loader import load_settings

sys.setrecursionlimit(10000)

app = typer.Typer(
    name="darkpattern",
    help="Autonomous dark pattern investigator.",
    add_completion=False
)

console = Console()


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, force=True)


@app.command()
def investigate(
    url: Annotated[str, typer.Option("--url", "-u", help="URL to investigate")],
    backend: Annotated[str, typer.Option("--backend", "-b", help="LLM backend: ollama | openai")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Output: terminal | json | both")] = "terminal",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed logs")] = False,
):
    """Investigate a website for dark patterns."""
    _setup_logging(verbose)
    settings = load_settings()

    if backend:
        settings["llm"]["extractor"]["backend"] = backend
        settings["llm"]["analyst"]["backend"] = backend

    console.print()
    console.print(f"[bold]🔍 Dark Pattern Detective[/bold] — investigating [cyan]{url}[/cyan]")
    console.print(f"[dim]Backend: {settings['llm']['analyst']['backend']} | Output: {output}[/dim]")
    console.print()

    start = time.time()

    # — investigate —
    console.print(f"[dim]⏳ Scraping and investigating — this takes 1-3 minutes...[/dim]")

    investigation_result = None
    try:
        investigation_result = run_investigation(url)
    except Exception as e:
        console.print(f"[red]✗ Investigation failed: {e}[/red]")
        sys.exit(1)

    # — analyse —
    console.print(f"[dim]📊 Analysing evidence...[/dim]")

    report = None
    try:
        report = analyze(
            evidence_summary=investigation_result.memory_summary,
            screenshot_paths=investigation_result.screenshots
        )
    except Exception as e:
        console.print(f"[red]✗ Analysis failed: {e}[/red]")
        sys.exit(1)

    elapsed = f"{time.time() - start:.0f}s"
    console.print(
        f"[green]✓[/green] Done in {elapsed} — "
        f"[bold]{investigation_result.step_count}[/bold] steps · "
        f"[bold]{len(investigation_result.screenshots)}[/bold] screenshots · "
        f"[bold]{report.pattern_count}[/bold] pattern{'s' if report.pattern_count != 1 else ''} found"
    )
    console.print()

    # — report —
    print_report(report, url, output=output)

    if report.overall_risk == "HIGH":
        sys.exit(2)
    elif report.overall_risk in ("MEDIUM", "LOW"):
        sys.exit(1)
    else:
        sys.exit(0)


@app.command()
def version():
    """Show version information."""
    console.print("[bold]Dark Pattern Detective[/bold] v0.1.0")


def main():
    app()


if __name__ == "__main__":
    main()