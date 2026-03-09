"""Textual TUI interface for file organizer."""

import json
from pathlib import Path
from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Button,
    Label,
    Input,
    Checkbox,
    Select,
    Static,
    DataTable,
    Collapsible,
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual.message import Message

from .organizer import FileOrganizer
from .config import RUNTIME_CONFIG, FILE_TYPE_MAPPINGS, CONFIG_PATH


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_size_bar(size_bytes: int, max_size: int, bar_width: int = 20) -> str:
    """Generate an ASCII bar representing relative size."""
    if max_size == 0:
        return "[" + " " * bar_width + "]"
    ratio = min(size_bytes / max_size, 1.0)
    filled = int(ratio * bar_width)
    return "[" + "=" * filled + " " * (bar_width - filled) + "]"


class AnalysisDialog(ModalScreen):
    """Modal dialog showing analysis results with collapsible categories."""

    CSS = """
    AnalysisDialog {
        align: center middle;
    }

    #dialog-container {
        width: 85;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }

    #summary-header {
        margin-bottom: 1;
        padding: 1;
        background: $panel;
    }

    #categories-container {
        height: auto;
        max-height: 70%;
        overflow-y: scroll;
    }

    Collapsible {
        margin: 0 0;
        padding: 0;
        border: solid $primary-darken-2;
        background: $surface-darken-1;
    }

    Collapsible CollapsibleTitle {
        background: $primary-darken-1;
        padding: 0 1;
    }

    Collapsible CollapsibleTitle:hover {
        background: $primary;
    }

    .category-header {
        text-style: bold;
    }

    .category-content {
        padding: 0 1;
        margin: 0;
    }

    #folders-section {
        margin-top: 1;
        padding: 1;
        background: $panel;
        border: solid $success;
    }

    .folders-title {
        text-style: bold;
        color: $success;
    }

    #buttons-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .stat-line {
        margin: 0;
    }

    .file-list {
        color: $text-muted;
        margin-left: 2;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    def __init__(self, distribution: dict, mode: str, directory: Path):
        super().__init__()
        self.distribution = distribution
        self.mode = mode
        self.directory = directory
        self.organizer = FileOrganizer()

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Container(id="dialog-container"):
            yield Label("📊 Directory Analysis Results", classes="dialog-title")

            # Summary header
            with Container(id="summary-header"):
                yield Static(id="summary-header-content")

            # Categories with collapsible sections
            with VerticalScroll(id="categories-container"):
                yield Static(id="categories-content")

            # Folders preview
            with Container(id="folders-section"):
                yield Label("📁 Folders to be Created", classes="folders-title")
                yield Static(id="folders-content")

            # Buttons
            with Horizontal(id="buttons-row"):
                yield Button("Close", id="close-btn", variant="primary")

    def on_mount(self) -> None:
        """Populate the dialog on mount."""
        self._populate_content()

    def _populate_content(self) -> None:
        """Populate all content sections."""
        counts = self.distribution.get("counts", {})
        sizes = self.distribution.get("sizes", {})

        total_count = sum(counts.values())
        total_size = sum(sizes.values())
        max_size = max(sizes.values()) if sizes else 1

        # Summary header
        header_lines = [
            f"[bold]Directory:[/] {self.directory}",
            f"[bold]Mode:[/] {self.mode}",
            f"[bold]Total Files:[/] {total_count}",
            f"[bold]Total Size:[/] {format_size(total_size)}",
        ]
        self.query_one("#summary-header-content", Static).update("\n".join(header_lines))

        # Categories content with collapsible sections
        categories = sorted(set(counts.keys()) | set(sizes.keys()), key=lambda c: sizes.get(c, 0), reverse=True)

        categories_lines = []
        for category in categories:
            count = counts.get(category, 0)
            size = sizes.get(category, 0)
            size_str = format_size(size)
            bar = get_size_bar(size, max_size, bar_width=12)
            percent = (size / total_size * 100) if total_size > 0 else 0
            count_percent = (count / total_count * 100) if total_count > 0 else 0

            # Get file types for this category
            extensions_info = ""
            if self.mode == "type" and category in FILE_TYPE_MAPPINGS:
                exts = list(FILE_TYPE_MAPPINGS[category])[:5]
                extensions_info = ", ".join(exts)
                if len(FILE_TYPE_MAPPINGS[category]) > 5:
                    extensions_info += "..."

            # Create collapsible section header
            categories_lines.append(f"[bold cyan]▼ {category}[/]")
            categories_lines.append(f"  {bar} {size_str:>12} ({percent:>5.1f}%) | {count:>4} files ({count_percent:>5.1f}%)")
            if extensions_info:
                categories_lines.append(f"  [dim]Extensions: {extensions_info}[/]")
            categories_lines.append("")

        self.query_one("#categories-content", Static).update("\n".join(categories_lines))

        # Folders preview
        folders_lines = []
        for category in categories:
            count = counts.get(category, 0)
            if count > 0:
                folders_lines.append(f"  [yellow]├──[/] [bold]{category}/[/] ({count} files)")
        self.query_one("#folders-content", Static).update("\n".join(folders_lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-btn":
            self.app.pop_screen()

    def action_close(self) -> None:
        """Close the dialog."""
        self.app.pop_screen()


class ConfigScreen(ModalScreen):
    """Modal screen for editing configuration settings with tabbed sections."""

    CSS = """
    ConfigScreen {
        align: center middle;
    }

    #config-container {
        width: 75;
        height: 35;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .config-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }

    #section-tabs {
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }

    .tab-btn {
        margin: 0 1;
        min-width: 12;
    }

    .tab-btn.active {
        background: $primary;
        text-style: bold;
    }

    #section-content {
        height: 12;
        padding: 0;
        background: $panel;
        border: solid $primary-darken-1;
    }
    
    #section-content VerticalScroll {
        height: 100%;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .config-row {
        margin: 1 0;
        height: auto;
    }

    .config-label {
        margin-bottom: 0;
    }

    Input, Select {
        width: 100%;
    }

    #config-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .error-message {
        color: $error;
        text-style: bold;
        margin-top: 1;
    }

    .success-message {
        color: $success;
        text-style: bold;
        margin-top: 1;
    }

    #config-status {
        margin-top: 1;
    }

    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("1", "select_size", "Size"),
        ("2", "select_date", "Date"),
        ("3", "select_ui", "UI"),
        ("4", "select_interactive", "Interactive"),
    ]

    def __init__(self):
        super().__init__()
        self._config_data = {}
        self._current_section = "size"

    def compose(self) -> ComposeResult:
        """Compose the configuration screen."""
        with Container(id="config-container"):
            yield Label("⚙️ Configuration Settings", classes="config-title")

            # Section tabs
            with Horizontal(id="section-tabs"):
                yield Button("📏 Size", id="tab-size", classes="tab-btn active")
                yield Button("📅 Date", id="tab-date", classes="tab-btn")
                yield Button("🎨 UI", id="tab-ui", classes="tab-btn")
                yield Button("🖱️ Interactive", id="tab-interactive", classes="tab-btn")

            # Section content containers (only one visible at a time)
            with Container(id="section-content"):
                # Size Settings Section
                with VerticalScroll(id="section-size"):
                    yield Label("Size Settings", classes="section-title")
                    with Vertical(classes="config-row"):
                        yield Label("Default Size Unit:", classes="config-label")
                        yield Select(
                            options=[
                                ("Bytes", "B"),
                                ("Kilobytes", "KB"),
                                ("Megabytes", "MB"),
                                ("Gigabytes", "GB"),
                            ],
                            value="MB",
                            id="default-unit-select",
                        )
                    with Vertical(classes="config-row"):
                        yield Label("Small File Threshold (MB):", classes="config-label")
                        yield Input(value="1", id="small-threshold-input")
                    with Vertical(classes="config-row"):
                        yield Label("Medium File Threshold (MB):", classes="config-label")
                        yield Input(value="100", id="medium-threshold-input")
                    with Vertical(classes="config-row"):
                        yield Label("Large File Threshold (MB):", classes="config-label")
                        yield Input(value="1024", id="large-threshold-input")
                    with Horizontal(classes="config-row"):
                        yield Checkbox("Show Bytes", value=False, id="show-bytes-checkbox")
                    with Horizontal(classes="config-row"):
                        yield Checkbox("Show Size in Tree View", value=True, id="show-size-tree-checkbox")
                    with Horizontal(classes="config-row"):
                        yield Checkbox("Auto-detect Size Units", value=True, id="auto-detect-units-checkbox")

                # Date Settings Section
                with VerticalScroll(id="section-date", classes="hidden"):
                    yield Label("Date Settings", classes="section-title")
                    with Vertical(classes="config-row"):
                        yield Label("Date Format:", classes="config-label")
                        yield Select(
                            options=[
                                ("YYYY-MM (2024-01)", "%Y-%m"),
                                ("YYYY-MM-DD (2024-01-15)", "%Y-%m-%d"),
                                ("YYYY (2024)", "%Y"),
                                ("MM-YYYY (01-2024)", "%m-%Y"),
                            ],
                            value="%Y-%m",
                            id="date-format-select",
                        )

                # UI Settings Section
                with VerticalScroll(id="section-ui", classes="hidden"):
                    yield Label("UI Settings", classes="section-title")
                    with Vertical(classes="config-row"):
                        yield Label("Bar Width:", classes="config-label")
                        yield Input(value="30", id="bar-width-input")
                    with Horizontal(classes="config-row"):
                        yield Checkbox("Colors Enabled", value=True, id="colors-enabled-checkbox")

                # Interactive Settings Section
                with VerticalScroll(id="section-interactive", classes="hidden"):
                    yield Label("Interactive Settings", classes="section-title")
                    with Vertical(classes="config-row"):
                        yield Label("Default Mode:", classes="config-label")
                        yield Select(
                            options=[
                                ("By File Type", "type"),
                                ("By Date", "date"),
                                ("By Size", "size"),
                            ],
                            value="type",
                            id="default-mode-select",
                        )

            yield Label("", id="config-status")

            with Horizontal(id="config-buttons"):
                yield Button("Save", id="save-config-btn", variant="success")
                yield Button("Reset to Defaults", id="reset-config-btn", variant="warning")
                yield Button("Cancel", id="cancel-config-btn", variant="error")

    def on_mount(self) -> None:
        """Load current configuration on mount."""
        self._load_config()

    def _switch_section(self, section: str) -> None:
        """Switch to a different configuration section."""
        self._current_section = section
        
        # Update tab button styles
        for tab_name in ["size", "date", "ui", "interactive"]:
            tab_btn = self.query_one(f"#tab-{tab_name}", Button)
            if tab_name == section:
                tab_btn.add_class("active")
            else:
                tab_btn.remove_class("active")
        
        # Show/hide section containers
        for section_name in ["size", "date", "ui", "interactive"]:
            section_container = self.query_one(f"#section-{section_name}", VerticalScroll)
            if section_name == section:
                section_container.remove_class("hidden")
            else:
                section_container.add_class("hidden")

    def action_select_size(self) -> None:
        """Select size section."""
        self._switch_section("size")

    def action_select_date(self) -> None:
        """Select date section."""
        self._switch_section("date")

    def action_select_ui(self) -> None:
        """Select UI section."""
        self._switch_section("ui")

    def action_select_interactive(self) -> None:
        """Select interactive section."""
        self._switch_section("interactive")

    def _load_config(self) -> None:
        """Load configuration values into form fields."""
        try:
            # Load from config file
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    self._config_data = json.load(f)
            else:
                self._config_data = {}

            # Size settings
            size_cfg = self._config_data.get("size", {})
            default_unit = size_cfg.get("default_unit", "MB")
            self.query_one("#default-unit-select", Select).value = default_unit
            self.query_one("#show-bytes-checkbox", Checkbox).value = size_cfg.get("show_bytes", False)

            thresholds = size_cfg.get("thresholds", {})
            small_mb = thresholds.get("small", 1048576) / (1024 * 1024)
            medium_mb = thresholds.get("medium", 104857600) / (1024 * 1024)
            self.query_one("#small-threshold-input", Input).value = str(int(small_mb))
            self.query_one("#medium-threshold-input", Input).value = str(int(medium_mb))

            # Date settings
            date_cfg = self._config_data.get("date", {})
            date_format = date_cfg.get("format", "%Y-%m")
            self.query_one("#date-format-select", Select).value = date_format

            # UI settings
            ui_cfg = self._config_data.get("ui", {})
            self.query_one("#bar-width-input", Input).value = str(ui_cfg.get("bar_width", 30))
            self.query_one("#colors-enabled-checkbox", Checkbox).value = ui_cfg.get("colors_enabled", True)

            # Interactive settings
            interactive_cfg = self._config_data.get("interactive", {})
            default_mode = interactive_cfg.get("default_mode", "type")
            self.query_one("#default-mode-select", Select).value = default_mode

        except Exception as e:
            self._show_status(f"Error loading config: {e}", error=True)

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            # Build config dict from form values
            config = {
                "size": {
                    "thresholds": {
                        "small": int(float(self.query_one("#small-threshold-input", Input).value) * 1024 * 1024),
                        "medium": int(float(self.query_one("#medium-threshold-input", Input).value) * 1024 * 1024),
                    },
                    "default_unit": self.query_one("#default-unit-select", Select).value,
                    "show_bytes": self.query_one("#show-bytes-checkbox", Checkbox).value,
                },
                "date": {
                    "format": self.query_one("#date-format-select", Select).value,
                },
                "extensions": self._config_data.get("extensions", {
                    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                    "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx"],
                    "videos": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"],
                    "audio": [".mp3", ".wav", ".ogg", ".flac", ".aac"],
                    "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                    "code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs"]
                }),
                "ui": {
                    "bar_width": int(self.query_one("#bar-width-input", Input).value),
                    "colors_enabled": self.query_one("#colors-enabled-checkbox", Checkbox).value,
                    "chart_style": "ascii",
                },
                "interactive": {
                    "default_mode": self.query_one("#default-mode-select", Select).value,
                },
            }

            # Write to config file
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)

            self._show_status("Configuration saved successfully!")
            self._config_data = config

        except ValueError as e:
            self._show_status(f"Invalid input value: {e}", error=True)
        except Exception as e:
            self._show_status(f"Error saving config: {e}", error=True)

    def _reset_config(self) -> None:
        """Reset configuration to defaults."""
        default_config = {
            "size": {
                "thresholds": {
                    "small": 1048576,
                    "medium": 104857600
                },
                "default_unit": "MB",
                "show_bytes": False
            },
            "date": {
                "format": "%Y-%m"
            },
            "extensions": {
                "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx"],
                "videos": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"],
                "audio": [".mp3", ".wav", ".ogg", ".flac", ".aac"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs"]
            },
            "ui": {
                "bar_width": 30,
                "colors_enabled": True,
                "chart_style": "ascii"
            },
            "interactive": {
                "default_mode": "type"
            }
        }

        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(default_config, f, indent=2)
            self._config_data = default_config
            self._load_config()
            self._show_status("Configuration reset to defaults!")
        except Exception as e:
            self._show_status(f"Error resetting config: {e}", error=True)

    def _show_status(self, message: str, error: bool = False) -> None:
        """Show a status message."""
        status_label = self.query_one("#config-status", Label)
        status_label.update(message)
        status_label.set_class(error, "error-message")
        status_label.set_class(not error, "success-message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "save-config-btn":
            self._save_config()
        elif button_id == "reset-config-btn":
            self._reset_config()
        elif button_id == "cancel-config-btn":
            self.app.pop_screen()
        elif button_id and button_id.startswith("tab-"):
            section = button_id.replace("tab-", "")
            self._switch_section(section)

    def action_close(self) -> None:
        """Close the config screen."""
        self.app.pop_screen()


class FileOrganizerForm(Screen):
    """Form screen for configuring file organization."""

    CSS = """
    FileOrganizerForm {
        align: center middle;
    }

    #form-container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .form-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .form-row {
        margin: 1 0;
        height: auto;
    }

    .form-label {
        margin-bottom: 0;
    }

    Input, Select {
        width: 100%;
    }

    #directory-input {
        width: 100%;
    }

    #buttons-container {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #analyze-btn {
        background: $primary;
    }

    #organize-btn {
        background: $success;
    }

    #cancel-btn {
        background: $error;
    }

    .error-message {
        color: $error;
        text-style: bold;
        margin-top: 1;
    }

    .success-message {
        color: $success;
        text-style: bold;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Organize"),
        ("s", "settings", "Settings"),
    ]

    class Organized(Message):
        """Message sent when organization is complete."""

        def __init__(self, summary: dict, directory: Path) -> None:
            self.summary = summary
            self.directory = directory
            super().__init__()

    def __init__(self, initial_directory: Optional[str] = None):
        super().__init__()
        self.initial_directory = initial_directory or "."
        self.organizer = FileOrganizer()
        self._distribution_data = {}
        self._current_mode = "type"

    def compose(self) -> ComposeResult:
        """Compose the form layout."""
        with Container(id="form-container"):
            yield Label("📁 File Organizer", classes="form-title")

            with Vertical(classes="form-row"):
                yield Label("Directory:", classes="form-label")
                yield Input(
                    value=self.initial_directory,
                    placeholder="Enter directory path to organize...",
                    id="directory-input",
                )

            with Vertical(classes="form-row"):
                yield Label("Organization Mode:", classes="form-label")
                yield Select(
                    options=[
                        ("By File Type", "type"),
                        ("By Date (YYYY-MM)", "date"),
                        ("By Size (small/medium/large)", "size"),
                    ],
                    value="type",
                    id="mode-select",
                )

            with Horizontal(classes="form-row"):
                yield Checkbox("Dry Run (preview only)", value=False, id="dry-run-checkbox")
                yield Checkbox("Show Statistics", value=True, id="stats-checkbox")

            with Horizontal(id="buttons-container"):
                yield Button("Analyze", id="analyze-btn", variant="primary")
                yield Button("Organize", id="organize-btn", variant="success")
                yield Button("Settings", id="settings-btn", variant="warning")
                yield Button("Cancel", id="cancel-btn", variant="error")

            yield Label("", id="status-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "analyze-btn":
            self._analyze_directory()
        elif button_id == "organize-btn":
            self._organize_files()
        elif button_id == "settings-btn":
            self.app.push_screen(ConfigScreen())
        elif button_id == "cancel-btn":
            self.app.exit()

    def action_cancel(self) -> None:
        """Cancel action."""
        self.app.exit()

    def action_submit(self) -> None:
        """Submit the form."""
        self._organize_files()

    def action_settings(self) -> None:
        """Open settings screen."""
        self.app.push_screen(ConfigScreen())

    def _get_directory(self) -> Optional[Path]:
        """Get and validate the directory path."""
        directory_input = self.query_one("#directory-input", Input)
        dir_path = Path(directory_input.value).resolve()
        if not dir_path.exists():
            self._show_error("Directory does not exist")
            return None
        if not dir_path.is_dir():
            self._show_error("Path is not a directory")
            return None
        return dir_path

    def _show_error(self, message: str) -> None:
        """Display an error message."""
        status_label = self.query_one("#status-label", Label)
        status_label.update(message)
        status_label.set_class(True, "error-message")
        status_label.set_class(False, "success-message")

    def _show_success(self, message: str) -> None:
        """Display a success message."""
        status_label = self.query_one("#status-label", Label)
        status_label.update(message)
        status_label.set_class(True, "success-message")
        status_label.set_class(False, "error-message")

    def _analyze_directory(self) -> None:
        """Analyze the directory and show results in a dialog."""
        dir_path = self._get_directory()
        if dir_path is None:
            return

        mode = self.query_one("#mode-select", Select).value
        self._current_mode = mode

        try:
            distribution = self.organizer.analyze_distribution(dir_path, mode)
            self._distribution_data = distribution
            total_files = sum(distribution.get("counts", {}).values())
            self._show_success(f"Found {total_files} files - See analysis dialog")
            # Push the analysis dialog
            self.app.push_screen(AnalysisDialog(distribution, mode, dir_path))
        except Exception as e:
            self._show_error(f"Error analyzing directory: {e}")

    def _organize_files(self) -> None:
        """Organize files based on form inputs."""
        dir_path = self._get_directory()
        if dir_path is None:
            return

        mode = self.query_one("#mode-select", Select).value
        dry_run = self.query_one("#dry-run-checkbox", Checkbox).value

        try:
            summary = self.organizer.organize_directory(
                dir_path, dry_run=dry_run, mode=mode
            )
            prefix = "Dry run " if dry_run else ""
            self._show_success(f"{prefix}Completed: {summary['processed']} items processed")
            self.post_message(self.Organized(summary, dir_path))
        except Exception as e:
            self._show_error(f"Error organizing files: {e}")


class ResultsScreen(Screen):
    """Screen showing organization results."""

    CSS = """
    ResultsScreen {
        align: center middle;
    }

    #results-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .results-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #summary-table {
        margin-top: 1;
        height: auto;
    }

    #stats-container {
        margin-top: 1;
        height: auto;
    }

    #buttons-container {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, summary: dict, directory: Path, show_stats: bool = True):
        super().__init__()
        self.summary = summary
        self.directory = directory
        self.show_stats = show_stats
        self.organizer = FileOrganizer()

    def compose(self) -> ComposeResult:
        """Compose the results screen."""
        with Container(id="results-container"):
            yield Label("✅ Organization Results", classes="results-title")

            yield Label(f"Directory: {self.directory}")
            yield Label(f"Mode: {self.summary.get('mode', 'type')}")
            yield Label(f"Total Items: {self.summary.get('total_files', 0)}")
            yield Label(f"Categories: {self.summary.get('categories', 0)}")

            yield DataTable(id="summary-table")

            if self.show_stats:
                with Container(id="stats-container"):
                    yield Label("Category Breakdown:")
                    yield Static(id="stats-output")

            with Horizontal(id="buttons-container"):
                yield Button("New Organization", id="new-btn", variant="primary")
                yield Button("Exit", id="exit-btn", variant="error")

    def on_mount(self) -> None:
        """Populate the results on mount."""
        table = self.query_one("#summary-table", DataTable)
        table.add_columns("Category", "Items Moved")

        moves = self.summary.get("moves", {})
        for category, items in sorted(moves.items()):
            table.add_row(category, str(len(items)))

        if self.show_stats:
            self._display_stats()

    def _display_stats(self) -> None:
        """Display statistics for each category."""
        stats_output = self.query_one("#stats-output", Static)
        lines = []

        moves = self.summary.get("moves", {})
        total_size = self.organizer.get_dir_size(self.directory) or 1

        for category, items in sorted(moves.items()):
            cat_dir = self.directory / category
            cat_size = (
                self.organizer.get_dir_size(cat_dir) if cat_dir.exists() else 0
            )
            percent = (cat_size / total_size) * 100 if total_size > 0 else 0
            size_str = format_size(cat_size)
            bar = get_size_bar(cat_size, total_size, bar_width=20)
            lines.append(f"  {category:<12} {bar} {size_str:>12} ({percent:>5.1f}%)")

        stats_output.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "new-btn":
            self.app.pop_screen()
        elif event.button.id == "exit-btn":
            self.app.exit()

    def action_back(self) -> None:
        """Go back to the form."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()


class FileOrganizerApp(App):
    """Main Textual application for file organization."""

    CSS = """
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    TITLE = "File Organizer"

    def __init__(self, initial_directory: Optional[str] = None):
        super().__init__()
        self.initial_directory = initial_directory

    def on_mount(self) -> None:
        """Push the form screen on mount."""
        self.push_screen(FileOrganizerForm(self.initial_directory))

    def on_file_organizer_form_organized(
        self, event: FileOrganizerForm.Organized
    ) -> None:
        """Handle the organized event from the form."""
        show_stats = True
        self.push_screen(ResultsScreen(event.summary, event.directory, show_stats))


def run_ui(directory: Optional[str] = None) -> None:
    """Entry point for the TUI application."""
    app = FileOrganizerApp(initial_directory=directory)
    app.run()


if __name__ == "__main__":
    run_ui()