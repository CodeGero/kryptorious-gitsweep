"""GitSweep CLI — main entry point."""

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="gitsweep")
def main():
    """GitSweep — Clean up your git repositories.

    Find stale branches, large files, and bloated history.
    Sweep it clean.
    """
    pass


@main.command()
@click.option("--repo", "-r", default=".", help="Path to git repository")
@click.option("--merged/--all", default=True, help="Show only merged branches")
@click.option("--stale", "-s", default=90, help="Days since last commit to consider stale")
@click.option("--delete/--dry-run", default=False, help="Delete branches (premium feature)")
def branches(repo, merged, stale, delete):
    """Find stale and merged branches."""
    from .commands import sweep_branches
    sweep_branches(repo=repo, merged_only=merged, stale_days=stale, delete=delete)


@main.command()
@click.option("--repo", "-r", default=".", help="Path to git repository")
@click.option("--size", "-s", default=1.0, help="Minimum file size in MB")
@click.option("--count", "-n", default=20, help="Number of largest files to show")
def large(repo, size, count):
    """Find large files bloating your repository."""
    from .commands import sweep_large
    sweep_large(repo=repo, min_size_mb=size, top_n=count)


@main.command()
@click.option("--repo", "-r", default=".", help="Path to git repository")
@click.option("--days", "-d", default=365, help="Days of history to analyze")
@click.option("--author", "-a", default=None, help="Filter by author email")
def history(repo, days, author):
    """Analyze commit history for bloat and patterns."""
    from .commands import sweep_history
    sweep_history(repo=repo, days=days, author=author)


@main.command()
@click.option("--repo", "-r", default=".", help="Path to git repository")
@click.option("--aggressive/--safe", default=False,
              help="Aggressive: delete merged+stale branches and drop size threshold")
def clean(repo, aggressive):
    """Sweep and clean a git repository.

    Safe mode (default) reports issues without deleting. Aggressive
    mode actually deletes merged-and-stale branches and flags smaller
    large files.

    \b
    Examples:
        gitsweep clean
        gitsweep clean --aggressive
    """
    from .commands import sweep_branches, sweep_large, sweep_history

    console.print()
    console.print(Panel(
        f"[bold]GitSweep Clean[/bold] — [cyan]{repo}[/cyan] "
        f"({'aggressive' if aggressive else 'safe'})",
        border_style="blue"))

    if aggressive:
        console.print("[yellow]Aggressive:[/yellow] will delete merged+stale branches.")
        sweep_branches(repo=repo, merged_only=True, stale_days=90, delete=True)
        sweep_large(repo=repo, min_size_mb=0.5, top_n=20)
    else:
        console.print("[dim]Safe mode: reporting only (no deletions).[/dim]")
        sweep_branches(repo=repo, merged_only=True, stale_days=90, delete=False)
        sweep_large(repo=repo, min_size_mb=1, top_n=10)
    sweep_history(repo=repo, days=90, author=None)


if __name__ == "__main__":
    main()
