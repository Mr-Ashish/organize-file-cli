# File Organizer CLI

A modular CLI tool to organize files in a folder by creating separate subfolders based on file types (e.g., images, documents) and moving files accordingly.

## Features
- Organization modes: --mode type (default, now incl. folders/), date (YYYY-MM), size (small/medium/large)
- Dry-run mode for preview
- Colorful progress bar + metrics summary on completion
- Modular design for extensions (custom mappings, recursive, etc.)
- Handles file name conflicts

## Installation
Use the included setup script for automated install + PATH config (recommended; single command).

```bash
# Run once:
./setup.sh
```

The CLI entrypoint `organize-files` is defined in pyproject.toml. (Manual: `pip install --user -e .` + PATH fix.)

Alternative (no install):
```bash
PYTHONPATH=src python -m file_organizer.cli <dir>
```

## Usage
```bash
# Organize current directory
organize-files

# Organize specific directory
organize-files /path/to/folder

# Dry run (short: -d)
organize-files -d

# By date or size (folders auto-included in type/size; short: -m)
organize-files -m date
organize-files --mode size

# With stats (short: -s)
organize-files -s

# Interactive (short: -i)
organize-files -i
```

## Project Structure
- `src/file_organizer/`: Main package
  - `organizer.py`: Core logic (extensible)
  - `config.py`: File type mappings
  - `cli.py`: Command-line interface
- `samples/`: Visible sample test files (used by tests; you can run tests/organizer on these manually)
- `tests/`: TDD test scripts (copies samples, runs CLI, verifies, auto-reverts)
- `LLM_GUIDELINES.md`: Guidelines for development

See `LLM_GUIDELINES.md` for more on extending the tool. Tests use sample files and auto-revert state after runs.
