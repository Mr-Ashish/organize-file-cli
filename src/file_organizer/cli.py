"""CLI interface for file organizer."""

import argparse
import sys
import time
from pathlib import Path

from .organizer import FileOrganizer
from .config import RUNTIME_CONFIG


def run_tui(directory: str = None):
    """Launch the Textual TUI interface."""
    try:
        from .ui import run_ui
        run_ui(directory)
    except ImportError as e:
        print(f"Error: Textual TUI not available. {e}", file=sys.stderr)
        print("Install textual with: pip install textual>=0.47.0", file=sys.stderr)
        sys.exit(1)


# ANSI colors for progress/summary (terminal-friendly)
class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    END = "\033[0m"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Organize files in a directory by type into separate folders."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to organize (default: current)",
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Simulate without moving files",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["type", "date", "size"],
        default="type",
        help="Organization mode: type (default, incl. folders), date (YYYY-MM), size (small/medium/large)",
    )
    parser.add_argument(
        "-s", "--stats",
        action="store_true",
        help="Show post-organize stats: dir sizes + visualized folder occupancy",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Enter interactive mode: prompts for options + shows file distribution chart",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="file-organizer 0.1.0",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the Textual TUI interface for interactive organization",
    )

    args = parser.parse_args()

    # Handle TUI mode
    if args.ui:
        run_tui(args.directory)
        return

    try:
        dir_path = Path(args.directory).resolve()
        organizer = FileOrganizer()

        if args.interactive:
            # Interactive: menu + chart + unit
            mode, dry_run, show_stats, unit = _interactive_prompts(dir_path, organizer)
            print(f"Organizing files in: {dir_path} (mode: {mode})")
            original_size = organizer.get_dir_size(dir_path) if show_stats else 0
        else:
            mode = args.mode
            dry_run = args.dry_run
            show_stats = args.stats
            unit = RUNTIME_CONFIG.get("size", {}).get("default_unit", "MB")
            print(f"Organizing files in: {dir_path} (mode: {mode})")
            original_size = organizer.get_dir_size(dir_path) if show_stats else 0

        summary = organizer.organize_directory(
            dir_path, dry_run=dry_run, mode=mode
        )

        if not dry_run:
            # Colorful progress bar
            total = summary["total_files"]
            print(f"{Colors.BLUE}Processing {total} items...{Colors.END}")
            bar_width = 40
            for i in range(bar_width + 1):
                progress = int((i / bar_width) * total)
                bar = "#" * i + "-" * (bar_width - i)
                print(f"\r{Colors.GREEN}[{bar}]{Colors.END} {progress}/{total} items", end="", flush=True)
                time.sleep(0.02)
            print("\n")

            # Final metrics
            print(f"{Colors.GREEN}{Colors.BOLD}Organization complete!{Colors.END}")
            print(f"{Colors.BLUE}Metrics (mode: {summary['mode']}):{Colors.END}")
            print(f"  Total items moved: {summary['total_files']}")
            print(f"  Categories used: {summary['categories']}")
            for category, items in summary["moves"].items():
                print(f"  - {Colors.YELLOW}{category}{Colors.END}: {len(items)} items moved")
            print(f"{Colors.GREEN}All items organized successfully!{Colors.END}")

            # Stats if flagged
            if show_stats:
                _print_stats(dir_path, original_size, summary, organizer)
        else:
            print(f"{Colors.YELLOW}Dry run completed.{Colors.END}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _print_stats(dir_path: Path, original_size: int, summary: dict, organizer: FileOrganizer):
    """Helper for visualized stats (modular; called only if --stats)."""
    final_size = organizer.get_dir_size(dir_path)
    print(f"{Colors.BLUE}Stats:{Colors.END}")
    print(f"  Original dir size: {original_size / (1024*1024):.2f} MB")
    print(f"  Final dir size: {final_size / (1024*1024):.2f} MB")

    # Visual bars for each category % occupancy
    total_size = final_size or 1
    max_bar = 30
    for category, items in summary["moves"].items():
        cat_dir = dir_path / category
        cat_size = organizer.get_dir_size(cat_dir) if cat_dir.exists() else 0
        percent = (cat_size / total_size) * 100
        bar_len = int((percent / 100) * max_bar)
        bar = "#" * bar_len + "-" * (max_bar - bar_len)
        print(f"  {Colors.YELLOW}{category}{Colors.END}: {cat_size / (1024*1024):.2f} MB "
              f"({percent:.1f}%) {Colors.GREEN}[{bar}]{Colors.END}")


def _print_distribution_chart(dist: dict, mode: str):
    """ASCII chart for interactive pre-analysis (counts + size bars)."""
    print(f"{Colors.BLUE}File distribution chart (by {mode}):{Colors.END}")
    max_count = max(dist["counts"].values(), default=1)
    max_size_bar = 20
    for cat, count in sorted(dist["counts"].items(), key=lambda x: -x[1]):
        size_mb = dist["sizes"].get(cat, 0) / (1024 * 1024)
        count_bar = "#" * int((count / max_count) * 20)
        size_bar_len = int((size_mb / max((dist["sizes"].values() or [1]), default=1) / (1024*1024)) * max_size_bar) if dist["sizes"] else 0
        size_bar = "#" * size_bar_len + "-" * (max_size_bar - size_bar_len)
        print(f"  {Colors.YELLOW}{cat}{Colors.END}: {count} items | {size_mb:.2f} MB "
              f"{Colors.GREEN}[{count_bar}]{Colors.END} (size: [{size_bar}])")


def _curses_menu(stdscr, title, options):
    """Curses menu: minimal height, central, light colors, borders, desc, arrows."""
    import curses  # Ensure in scope for menu
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Title light cyan
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Highlight light white/blue
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Desc
    current = 0
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        # Minimal draw area (top-centered, not full height)
        start_y = max(0, height // 4)  # Start higher for minimal feel
        # Title + border
        title_x = width // 2 - len(title) // 2
        stdscr.addstr(start_y, title_x, title, curses.A_BOLD | curses.color_pair(1))
        stdscr.addstr(start_y + 1, title_x - 2, "=" * (len(title) + 4), curses.color_pair(1))
        # Options (with desc, borders, highlight)
        for i, (opt, desc) in enumerate(options):
            y = start_y + 3 + i * 2  # Space for desc
            if y >= height - 2:
                break  # Minimal height
            opt_x = width // 2 - len(opt) // 2 - 5
            if i == current:
                stdscr.addstr(y, opt_x, f"> [ {opt} ] <", curses.A_REVERSE | curses.color_pair(2))
            else:
                stdscr.addstr(y, opt_x, f"  [ {opt} ]  ", curses.A_NORMAL)
            # Desc in yellow, different color
            desc_x = width // 2 - len(desc) // 2
            stdscr.addstr(y + 1, desc_x, desc, curses.color_pair(3))
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and current > 0:
            current -= 1
        elif key == curses.KEY_DOWN and current < len(options) - 1:
            current += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[current][0]

def _interactive_prompts(dir_path: Path, organizer: FileOrganizer):
    """Curses interactive (arrows, centered, bordered) + chart + unit."""
    print(f"{Colors.BOLD}Interactive mode for {dir_path}{Colors.END}")
    # Chart first
    dist = organizer.analyze_distribution(dir_path, "type")
    _print_distribution_chart(dist, "type")

    # Curses for mode select (minimal height, central, light colors, bordered options + desc)
    import curses  # Local; fallback if no tty
    mode_options = [
        ("type", "by extension (incl. folders)"),
        ("date", "by year-month from file date"),
        ("size", "by file size (small/medium/large)"),
    ]
    try:
        mode = curses.wrapper(lambda stdscr: _curses_menu(stdscr, "Select Mode", mode_options))
    except Exception as e:
        import traceback
        print(f"Note: Curses menu failed ({e}). Full error:\n{traceback.format_exc()}")
        print("Using numbered fallback (arrows not available in this env).")
        # Numbered fallback for navigation
        print(f"\n{Colors.BLUE}Choose mode:{Colors.END}")
        for i, (opt, desc) in enumerate(mode_options, 1):
            print(f"  {i}. {opt} - {desc}")
        mode_idx = input("Enter number [1]: ").strip() or "1"
        mode = mode_options[int(mode_idx) - 1][0] if mode_idx.isdigit() and 1 <= int(mode_idx) <= len(mode_options) else "type"

    # Other prompts
    dry_str = input("\nDry-run only? (y/n) [n]: ").strip().lower() or "n"
    dry_run = dry_str in ("y", "yes")
    stats_str = input("Show stats after? (y/n) [y]: ").strip().lower() or "y"
    show_stats = stats_str in ("y", "yes")
    unit = input("Size unit (bytes/KB/MB/GB) [MB]: ").strip().upper() or "MB"

    # Re-chart
    if mode != "type":
        dist = organizer.analyze_distribution(dir_path, mode)
        _print_distribution_chart(dist, mode)
    print(f"{Colors.GREEN}Proceeding...{Colors.END}")
    return mode, dry_run, show_stats, unit


if __name__ == "__main__":
    main()
