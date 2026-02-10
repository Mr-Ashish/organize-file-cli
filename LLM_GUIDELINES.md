# LLM Guidelines for Zed-Base Project

## Project Overview
This is a CLI tool for organizing files in directories based on file types. The goal is to keep it modular for future extensions like custom rules, dry-run, etc.

## Coding Standards
- Follow PEP 8 for Python code.
- Use type hints where possible.
- Keep functions small and single-responsibility.
- Modular design: separate core logic, CLI, config.
- Write docstrings for all public functions/classes.
- Include unit tests for core functionality (future).

## File Organization
- Core logic in src/file_organizer/organizer.py
- CLI in src/file_organizer/cli.py
- Configurations in src/file_organizer/config.py
- Use relative imports.

## Extension Guidelines
- To add new features, extend the Organizer class or add strategies.
- Keep CLI commands extensible with subcommands.

## Testing
- Use stdlib unittest for TDD tests (in tests/).
- Tests create sample files, run CLI, verify, and revert state.

## Commit Messages
- Use conventional commits: feat, fix, docs, etc.

## AI Assistance
- When suggesting code, ensure it's modular and follows above.
- Prefer composition over inheritance.
