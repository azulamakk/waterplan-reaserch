from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from waterplan.config import get_model, get_settings

app = typer.Typer(
    name="waterplan-research",
    help="Automated water risk intelligence tool. Researches water stress, incidents, and regulations for industrial locations.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _resolve_output_path(output: Optional[str]) -> Optional[Path]:
    return Path(output) if output else None


@app.command()
def research(
    locations: List[str] = typer.Argument(
        default=None,
        help='Location(s) to research. E.g. "Mexicali, Mexico" "Chandler, Arizona, USA"',
    ),
    model: str = typer.Option(
        None,
        "--model", "-m",
        help="AI model to use. Supported: claude-sonnet-4-6, claude-haiku-4-5-20251001, gpt-4o, gpt-4o-mini, llama3.1, etc.",
    ),
    compare_models: bool = typer.Option(
        False,
        "--compare-models",
        help="Run all configured models and produce a comparison report.",
    ),
    models_list: Optional[str] = typer.Option(
        None,
        "--models",
        help="Comma-separated list of models to compare (used with --compare-models).",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path. Extension determines format: .md, .csv, .pdf",
    ),
    locations_file: Optional[Path] = typer.Option(
        None,
        "--locations-file",
        help="Path to a text file with one location per line.",
        exists=True,
    ),
    concurrency: int = typer.Option(
        1,
        "--concurrency",
        help="Number of locations to process in parallel.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Disable caching of search results and page fetches.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed agent tool calls during execution.",
    ),
    clear_cache: bool = typer.Option(
        False,
        "--clear-cache",
        help="Clear the local cache before running.",
    ),
):
    """Research water risks for one or more industrial locations."""
    from waterplan.cache.store import get_cache

    if clear_cache:
        get_cache().clear()
        console.print("[green]Cache cleared.[/green]")

    settings = get_settings()
    use_cache = not no_cache

    # Collect all locations
    all_locations = list(locations or [])
    if locations_file:
        extra = [l.strip() for l in locations_file.read_text().splitlines() if l.strip()]
        all_locations.extend(extra)

    if not all_locations:
        err_console.print("[red]Error: No locations provided.[/red]")
        raise typer.Exit(1)

    from waterplan.search.provider import provider_name
    console.print(f"[dim]Search provider: {provider_name()}[/dim]")

    output_path = _resolve_output_path(output)
    reports = []

    if compare_models:
        from waterplan.comparison.runner import compare_models as run_comparison
        from waterplan.output.markdown import format_full_comparison

        model_ids = None
        if models_list:
            model_ids = [m.strip() for m in models_list.split(",")]

        for location in all_locations:
            console.print(Panel(f"[bold blue]Comparing models for:[/bold blue] {location}", expand=False))
            comparison = run_comparison(
                location=location,
                models=model_ids,
                use_cache=use_cache,
                verbose=verbose,
                max_workers=concurrency,
            )
            md_text = format_full_comparison(comparison)
            console.print(Markdown(md_text))

            if output_path:
                _save_comparison(comparison, output_path)
    else:
        from waterplan.agent.research_agent import research_location
        from waterplan.output.markdown import format_report

        model_id = model or settings.default_model

        if concurrency > 1:
            import concurrent.futures
            import time as _time

            def _research_with_retry(loc, model_id, use_cache, verbose):
                """Run research_location with one retry on sustained rate limit."""
                for attempt in range(2):
                    try:
                        return research_location(
                            loc, get_model(model_id), model_id, use_cache, verbose
                        )
                    except Exception as e:
                        if attempt == 0 and ("429" in str(e) or "rate_limit" in str(e).lower()):
                            _time.sleep(30)  # back off 30s then retry once
                            continue
                        raise

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {}
                for i, loc in enumerate(all_locations):
                    if i > 0:
                        _time.sleep(3)  # stagger starts to spread token usage over time
                    futures[executor.submit(_research_with_retry, loc, model_id, use_cache, verbose)] = loc

                for future in concurrent.futures.as_completed(futures):
                    loc = futures[future]
                    try:
                        report = future.result()
                        reports.append(report)
                        console.print(Markdown(format_report(report)))
                    except Exception as e:
                        err_console.print(f"[red]Failed for {loc}: {e}[/red]")
        else:
            for location in all_locations:
                console.print(Panel(
                    f"[bold blue]Researching:[/bold blue] {location}  |  Model: [cyan]{model_id}[/cyan]",
                    expand=False,
                ))
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    task = progress.add_task("Running research agent...", total=None)
                    report = research_location(
                        location=location,
                        model=get_model(model_id),
                        model_id=model_id,
                        use_cache=use_cache,
                        verbose=verbose,
                    )
                    progress.remove_task(task)

                md_text = format_report(report)
                console.print(Markdown(md_text))
                reports.append(report)

        if output_path and reports:
            _save_reports(reports, output_path)


def _save_reports(reports, path: Path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        from waterplan.output.csv_writer import write_csv
        write_csv(reports, path)
        console.print(f"[green]CSV saved → {path}[/green]")
    elif suffix == ".pdf":
        from waterplan.output.pdf_generator import write_pdf
        write_pdf(reports, path)
        console.print(f"[green]PDF saved → {path}[/green]")
    else:
        from waterplan.output.markdown import format_report
        content = "\n\n---\n\n".join(format_report(r) for r in reports)
        path.write_text(content, encoding="utf-8")
        console.print(f"[green]Markdown saved → {path}[/green]")


def _save_comparison(comparison, path: Path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        from waterplan.output.csv_writer import write_csv
        write_csv(list(comparison.results.values()), path)
        console.print(f"[green]CSV saved → {path}[/green]")
    elif suffix == ".pdf":
        from waterplan.output.pdf_generator import write_pdf
        write_pdf(list(comparison.results.values()), path)
        console.print(f"[green]PDF saved → {path}[/green]")
    else:
        from waterplan.output.markdown import format_full_comparison
        path.write_text(format_full_comparison(comparison), encoding="utf-8")
        console.print(f"[green]Markdown saved → {path}[/green]")


@app.command()
def cache_info():
    """Show cache statistics."""
    from waterplan.cache.store import get_cache
    stats = get_cache().stats()
    console.print(f"Cache entries: {stats['count']}")
    console.print(f"Cache size: {stats['size_mb']} MB")
    console.print(f"Cache location: {get_settings().cache_dir}")


@app.command()
def search_provider():
    """Show active search provider and available options."""
    from waterplan.search.provider import provider_name
    from waterplan.search.searxng_client import SearXNGClient
    import os

    console.print(f"\n[bold]Active search provider:[/bold] [green]{provider_name()}[/green]\n")
    console.print("[bold]Available providers (priority order):[/bold]")

    searxng_running = SearXNGClient().is_available()
    searxng_status = "[green]RUNNING[/green]" if searxng_running else "[red]not running[/red]"
    console.print(f"\n  1. [cyan]SearXNG[/cyan] (self-hosted, free, unlimited)  — {searxng_status}")
    console.print("     Start: [dim]docker run -d -p 8080:8080 searxng/searxng[/dim]")
    console.print("     Set:   [dim]SEARXNG_URL=http://localhost:8080[/dim]")

    brave = "[green]configured[/green]" if os.getenv("BRAVE_SEARCH_API_KEY") else "[dim]not set[/dim]"
    console.print(f"\n  2. [cyan]Brave Search[/cyan] (2,000 free/mo)            — {brave}")
    console.print("     Set:   [dim]BRAVE_SEARCH_API_KEY=...[/dim]")

    serper = "[green]configured[/green]" if os.getenv("SERPER_API_KEY") else "[dim]not set[/dim]"
    console.print(f"\n  3. [cyan]Serper.dev[/cyan] (2,500 free, $0.001/q after)  — {serper}")
    console.print("     Set:   [dim]SERPER_API_KEY=...[/dim]")

    console.print(f"\n  4. [cyan]DuckDuckGo[/cyan] (default, rate-limited)        — [yellow]fallback[/yellow]")


@app.command()
def models():
    """List supported AI models."""
    import os
    from waterplan.agent.self_critic import _pick_judge_model

    console.print("[bold]Supported models:[/bold]")
    console.print("\n[cyan]Anthropic Claude (requires ANTHROPIC_API_KEY):[/cyan]")
    console.print("  claude-sonnet-4-6         — Best quality (recommended)")
    console.print("  claude-haiku-4-5-20251001 — $0.80/$4.00 per MTok in/out")
    console.print("\n[cyan]OpenAI (requires OPENAI_API_KEY):[/cyan]")
    console.print("  gpt-5-mini                — 500k TPM Tier 1 (recommended for batches)")
    console.print("  gpt-4o                    — Best OpenAI quality")
    console.print("  gpt-4o-mini               — $0.15/$0.60 per MTok in/out (200k TPM Tier 1)")
    console.print("\n[cyan]Ollama (local, no API key needed):[/cyan]")
    console.print("  llama3.1                  — Run: ollama pull llama3.1")
    console.print("  qwen2.5                   — Run: ollama pull qwen2.5")
    console.print("  mistral                   — Run: ollama pull mistral")

    judge = _pick_judge_model()
    console.print(f"\n[bold]Auto-selected self-critique judge:[/bold] [green]{judge}[/green]")
    console.print("  (cheapest available model — gpt-4o-mini preferred over claude-haiku)")
