"""Core file organization logic."""

import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from .config import (
    FILE_TYPE_MAPPINGS,
    IGNORED,
    SIZE_THRESHOLDS,
    FOLDERS_CATEGORY,
    KNOWN_CATEGORIES,
    RUNTIME_CONFIG,
    DATE_FORMAT,
)


class FileOrganizer:
    """Modular file organizer class for extensibility."""

    def __init__(self, mappings: Dict[str, Set[str]] = None):
        """Initialize with optional custom mappings."""
        self.mappings = mappings or FILE_TYPE_MAPPINGS
        self.other_category = "other"

    def get_category(self, item: Path, mode: str = "type") -> str:
        """Get category based on mode (type/date/size). Modular for extensions."""
        if mode == "type":
            if item.is_dir():
                return FOLDERS_CATEGORY  # Add folders as type
            if item.is_file():
                ext = item.suffix.lower()
                for category, extensions in self.mappings.items():
                    if ext in extensions:
                        return category
                return self.other_category
            return None
        elif mode == "date":
            # Group by configured date format from mtime
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            return mtime.strftime(DATE_FORMAT)
        elif mode == "size":
            if item.is_dir():
                return FOLDERS_CATEGORY
            if item.is_file():
                size = item.stat().st_size
                if size < SIZE_THRESHOLDS["small"]:
                    return "small"
                elif size < SIZE_THRESHOLDS["medium"]:
                    return "medium"
                return "large"
            return None
        return self.other_category

    def organize_directory(self, directory: Path, dry_run: bool = False, mode: str = "type") -> dict:
        """Organize by mode (type/date/size); returns summary. Handles folders in type/size."""
        if not directory.exists():
            raise FileNotFoundError(f"Directory {directory} does not exist")

        # Collect by mode category
        files_by_category: Dict[str, List[Path]] = defaultdict(list)
        for item in directory.iterdir():
            if item.name in IGNORED:
                continue
            # Skip nested + known category dirs (fallback for re-runs/edge case to avoid self-move)
            if item.is_dir() and not self._should_process_dir(item):
                if item.name in KNOWN_CATEGORIES or (mode == "date" and len(item.name) == 7 and item.name[4] == "-"):
                    continue  # Already organized; skip to prevent nesting
                if mode in ("type", "size"):
                    # Move other top-level folders
                    files_by_category[FOLDERS_CATEGORY].append(item)
                continue
            category = self.get_category(item, mode)
            if category:
                files_by_category[category].append(item)

        total_files = sum(len(files) for files in files_by_category.values())

        # Process moves
        moves = {}
        processed = 0
        for category, items in files_by_category.items():
            if not items:
                continue
            category_dir = directory / category
            if not dry_run:
                category_dir.mkdir(exist_ok=True)
            moves[category] = []
            for item in items:
                target = category_dir / item.name
                # Fallback: skip self-move (e.g., existing folders/ dir)
                if target == item or (target.exists() and target.is_relative_to(item)):
                    continue
                if dry_run:
                    # Relative for clean output: filename -> category/filename
                    rel_target = f"{category}/{item.name}"
                    print(f"Would move: {item.name} -> {rel_target}")
                else:
                    if target.exists():
                        target = self._get_unique_path(target)
                    shutil.move(str(item), str(target))
                moves[category].append(target)
                processed += 1

        return {
            "moves": moves,
            "total_files": total_files,
            "categories": len(moves),
            "processed": processed,
            "mode": mode,
        }

    def _should_process_dir(self, dir_path: Path) -> bool:
        """Decide if subdir should be processed. For MVP, skip all subdirs."""
        return False  # Extendable for recursive

    def _get_unique_path(self, path: Path) -> Path:
        """Get unique path if conflict."""
        counter = 1
        original = path
        while path.exists():
            path = original.with_name(f"{original.stem}_{counter}{original.suffix}")
            counter += 1
        return path

    def get_dir_size(self, directory: Path) -> int:
        """Recursive dir size in bytes (for stats)."""
        total = 0
        for path in directory.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def analyze_distribution(self, directory: Path, mode: str = "type") -> dict:
        """Pre-analysis for interactive: counts/sizes by category (for chart)."""
        counts: Dict[str, int] = defaultdict(int)
        sizes: Dict[str, int] = defaultdict(int)
        for item in directory.iterdir():
            if item.name in IGNORED or (item.is_dir() and item.name in KNOWN_CATEGORIES):
                continue
            category = self.get_category(item, mode)
            if category:
                counts[category] += 1
                if item.is_file():
                    sizes[category] += item.stat().st_size
        return {"counts": dict(counts), "sizes": dict(sizes)}
