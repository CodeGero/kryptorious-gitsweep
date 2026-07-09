"""GitSweep commands."""

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import git
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def _get_repo(repo_path: str) -> git.Repo:
    """Get git repo object, searching upward if needed."""
    path = Path(repo_path).resolve()
    try:
        return git.Repo(path, search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        console.print(f"[red]Error:[/red] Not a git repository: {path}")
        raise SystemExit(1)


def sweep_branches(repo: str = ".", merged_only: bool = True,
                   stale_days: int = 90, delete: bool = False):
    """Find stale and merged branches."""
    r = _get_repo(repo)
    console.print()
    console.print(Panel(f"[bold]GitSweep — Branches[/bold] in [cyan]{Path(r.working_dir).name}[/cyan]",
                        border_style="blue"))

    try:
        main_branch = r.active_branch.name
    except (TypeError, ValueError):
        # Detached HEAD — try to find main
        for candidate in ["main", "master"]:
            if candidate in r.heads:
                main_branch = candidate
                break
        else:
            main_branch = list(r.heads)[0].name if r.heads else "main"

    console.print(f"Main branch: [bold]{main_branch}[/bold]")

    stale_date = datetime.now(timezone.utc) - timedelta(days=stale_days)
    candidates = []

    for branch in r.heads:
        if branch.name == main_branch:
            continue

        commit = branch.commit
        commit_date = commit.committed_datetime

        # Check if merged
        is_merged = False
        try:
            r.git.merge_base("--is-ancestor", branch.name, main_branch)
            is_merged = True
        except git.GitCommandError:
            is_merged = False

        # Check if stale
        is_stale = commit_date.replace(tzinfo=timezone.utc) < stale_date

        if merged_only and not is_merged:
            continue

        candidates.append({
            "name": branch.name,
            "last_commit": commit_date.strftime("%Y-%m-%d"),
            "author": commit.author.name,
            "message": commit.message.split("\n")[0][:60],
            "merged": is_merged,
            "stale": is_stale,
        })

    # Sort: merged first, then by date
    candidates.sort(key=lambda b: (not b["merged"], b["last_commit"]))

    if not candidates:
        console.print("[green]No stale or merged branches found. Repo is clean![/green]")
        return

    table = Table(title=f"Found {len(candidates)} branches to sweep")
    table.add_column("Branch", style="cyan")
    table.add_column("Last Commit", style="dim")
    table.add_column("Author")
    table.add_column("Status")
    table.add_column("Message")

    for b in candidates:
        status = []
        if b["merged"]:
            status.append("[green]merged[/green]")
        if b["stale"]:
            status.append("[yellow]stale[/yellow]")
        table.add_row(
            b["name"],
            b["last_commit"],
            b["author"],
            " ".join(status),
            b["message"][:50]
        )

    console.print(table)
    console.print()

    if delete:
        console.print("[red]Branch deletion is a premium feature.[/red]")
        console.print("Upgrade at https://kryptorious.gumroad.com/l/jbvet")
    else:
        console.print("[yellow]Run with --delete to remove these branches (premium feature)[/yellow]")
        console.print("Free version: copy these commands to delete manually:")
        console.print()
        for b in candidates:
            console.print(f"  git branch -d {b['name']}")


def sweep_large(repo: str = ".", min_size_mb: float = 1.0, top_n: int = 20):
    """Find large files in git history."""
    r = _get_repo(repo)
    console.print()
    console.print(Panel(f"[bold]GitSweep — Large Files[/bold] in [cyan]{Path(r.working_dir).name}[/cyan]",
                        border_style="blue"))

    # Use git rev-list to find large objects
    try:
        # Find large files in HEAD
        result = r.git.rev_list("--objects", "--all")
        objects = {}
        for line in result.split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    size = r.git.cat_file("-s", parts[0])
                    size_bytes = int(size.strip())
                    if size_bytes >= min_size_mb * 1024 * 1024:
                        objects[parts[1] if len(parts) > 1 else parts[0]] = size_bytes
                except (git.GitCommandError, ValueError):
                    pass
    except git.GitCommandError:
        console.print("[yellow]Could not analyze git objects. Trying alternative method...[/yellow]")
        objects = {}

    # Also find large tracked files in working tree
    for root, dirs, files in os.walk(r.working_dir):
        if ".git" in root:
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
                if size >= min_size_mb * 1024 * 1024:
                    rel_path = os.path.relpath(fp, r.working_dir)
                    objects[rel_path] = size
            except OSError:
                pass

    if not objects:
        console.print(f"[green]No files larger than {min_size_mb}MB found![/green]")
        return

    # Sort by size descending
    sorted_files = sorted(objects.items(), key=lambda x: x[1], reverse=True)[:top_n]

    table = Table(title=f"Largest Files (>{min_size_mb}MB)")
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right")

    for path, size_bytes in sorted_files:
        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size_bytes / 1024:.1f} KB"
        table.add_row(path, size_str)

    console.print(table)

    total_size = sum(s for _, s in sorted_files)
    console.print(f"\nTotal: [bold]{total_size / (1024 * 1024):.1f} MB[/bold] in {len(sorted_files)} files")

    # Show git-filter-repo command for cleanup
    console.print()
    console.print("[yellow]To clean large files from history (premium feature):[/yellow]")
    console.print("Upgrade at https://kryptorious.gumroad.com/l/jbvet")
    console.print()
    console.print("Free tip: Use [bold]git-filter-repo[/bold] or [bold]BFG Repo-Cleaner[/bold]")


def sweep_history(repo: str = ".", days: int = 365, author: str = None):
    """Analyze commit history."""
    r = _get_repo(repo)
    console.print()
    console.print(Panel(f"[bold]GitSweep — History[/bold] in [cyan]{Path(r.working_dir).name}[/cyan]",
                        border_style="blue"))

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Collect stats
    try:
        commits = list(r.iter_commits(since=since.isoformat()))
    except (ValueError, git.GitCommandError):
        console.print("No commits found in this repository.")
        return
    if author:
        commits = [c for c in commits if c.author.email == author]

    if not commits:
        console.print(f"No commits in the last {days} days.")
        return

    # Author stats
    author_stats = {}
    for c in commits:
        email = c.author.email
        if email not in author_stats:
            author_stats[email] = {"name": c.author.name, "commits": 0, "insertions": 0, "deletions": 0}
        author_stats[email]["commits"] += 1
        try:
            stats = c.stats
            author_stats[email]["insertions"] += stats.total.get("insertions", 0)
            author_stats[email]["deletions"] += stats.total.get("deletions", 0)
        except Exception:
            pass

    console.print(f"[bold]Last {days} days:[/bold] {len(commits)} commits by {len(author_stats)} authors")
    console.print()

    table = Table(title="Author Breakdown")
    table.add_column("Author")
    table.add_column("Commits", justify="right")
    table.add_column("Insertions", justify="right")
    table.add_column("Deletions", justify="right")
    table.add_column("Net", justify="right")

    for email, stats in sorted(author_stats.items(), key=lambda x: x[1]["commits"], reverse=True):
        net = stats["insertions"] - stats["deletions"]
        net_style = f"[green]+{net:,}[/green]" if net >= 0 else f"[red]{net:,}[/red]"
        table.add_row(
            stats["name"],
            str(stats["commits"]),
            f"[green]{stats['insertions']:,}[/green]",
            f"[red]{stats['deletions']:,}[/red]",
            net_style
        )

    console.print(table)

    # Weekday patterns
    weekday_counts = {i: 0 for i in range(7)}
    for c in commits:
        weekday_counts[c.committed_datetime.weekday()] += 1

    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    console.print()
    console.print("[bold]Commit activity by day:[/bold]")
    max_count = max(weekday_counts.values()) if weekday_counts else 1
    for i in range(7):
        bar_len = int(weekday_counts[i] / max_count * 30) if max_count > 0 else 0
        bar = "█" * bar_len
        console.print(f"  {days_names[i]}: {bar} {weekday_counts[i]}")

    # File churn
    file_changes = {}
    for c in commits:
        try:
            for fpath, change in c.stats.files.items():
                if fpath not in file_changes:
                    file_changes[fpath] = 0
                file_changes[fpath] += change.get("lines", 0) or (change.get("insertions", 0) + change.get("deletions", 0))
        except Exception:
            pass

    if file_changes:
        top_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:10]
        console.print()
        console.print("[bold]Most changed files:[/bold]")
        for fpath, changes in top_files:
            console.print(f"  {changes:>6,}  {fpath}")
