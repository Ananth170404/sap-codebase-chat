"""
file_processor.py
─────────────────
Walks a project directory, reads every readable file, and builds a rich
context string to pass to Gemini.  Handles the full set of file types
found in SAP CPI / Integration Suite projects as well as common
programming files.
"""

from __future__ import annotations

import os
from pathlib import Path
from collections import defaultdict
from typing import Tuple  # noqa: F401 – kept for IDE hints on older Pythons

# ─────────────────────────────────────────────────────────────────
# File-type configuration
# ─────────────────────────────────────────────────────────────────

# Files we try to read as UTF-8 text
TEXT_EXTENSIONS: set[str] = {
    # SAP CPI / Integration Suite
    ".iflw",        # Integration Flow (BPMN/XML)
    ".prop",        # Properties
    ".propdef",     # Property definitions
    ".mf",          # Manifest (MANIFEST.MF)
    # Scripting
    ".groovy",      # Groovy scripts (very common in SAP CPI)
    ".java",
    ".js",
    ".ts",
    ".py",
    ".rb",
    ".sh",
    ".bat",
    # Data / Config
    ".xml",
    ".xsd",
    ".wsdl",
    ".xsl",
    ".xslt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".properties",
    ".env",
    ".cfg",
    ".conf",
    # Documentation
    ".md",
    ".txt",
    ".rst",
    ".adoc",
    # Build
    ".gradle",
    ".pom",
        ".project",      # Eclipse / SAP project file (often no ext inside .project)
    ".classpath",
    # SQL
    ".sql",
    # Web
    ".html",
    ".css",
    ".csv",
}

# Extension -> human-readable language label (for markdown code fences)
LANG_MAP: dict[str, str] = {
    ".iflw":      "xml",
    ".xml":       "xml",
    ".xsd":       "xml",
    ".wsdl":      "xml",
    ".xsl":       "xml",
    ".xslt":      "xml",
    ".groovy":    "groovy",
    ".java":      "java",
    ".js":        "javascript",
    ".ts":        "typescript",
    ".py":        "python",
    ".sh":        "bash",
    ".bat":       "batch",
    ".json":      "json",
    ".yaml":      "yaml",
    ".yml":       "yaml",
    ".toml":      "toml",
    ".sql":       "sql",
    ".html":      "html",
    ".css":       "css",
    ".md":        "markdown",
    ".gradle":    "groovy",
}

# Images we read as binary (passed to Gemini vision when user attaches them)
IMAGE_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
}

# Files / dirs to skip silently
SKIP_NAMES: set[str] = {
    ".git", ".svn", ".hg",
    "__pycache__", "node_modules", ".DS_Store",
    "Thumbs.db",
}

MAX_FILE_SIZE_BYTES = 500_000   # 500 KB – skip very large binary-ish files
MAX_CONTEXT_CHARS   = 900_000   # ~225 k tokens – stay under Gemini's 1 M limit


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

def build_directory_tree(root_path: str) -> str:
    """Return a pretty-printed directory tree string."""
    root = Path(root_path)
    lines: list[str] = [root.name + "/"]

    def _walk(path: Path, prefix: str = "") -> None:
        try:
            entries = sorted(
                path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except PermissionError:
            return

        entries = [e for e in entries if e.name not in SKIP_NAMES]
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension)

    _walk(root)
    return "\n".join(lines)


def get_file_type_summary(root_path: str) -> dict[str, int]:
    """Count files by extension."""
    counter: dict[str, int] = defaultdict(int)
    root = Path(root_path)
    for p in root.rglob("*"):
        if p.is_file() and not any(s in p.parts for s in SKIP_NAMES):
            counter[p.suffix.lower()] += 1
    return dict(counter)


def build_codebase_context(root_path: str) -> tuple[str, dict[str, bytes]]:
    """
    Walk *root_path* and return:
        context_str  – a Markdown string with directory tree + all file contents
        image_files  – {relative_path: bytes} for binary image files found
    """
    root = Path(root_path)
    tree = build_directory_tree(root_path)

    parts: list[str] = []
    image_files: dict[str, bytes] = {}
    total_chars = 0
    skipped: list[str] = []

    # Collect all files, sort for deterministic order
    all_files = sorted(
        (p for p in root.rglob("*") if p.is_file()),
        key=lambda p: str(p),
    )

    for file_path in all_files:
        # Skip hidden system dirs
        if any(part in SKIP_NAMES for part in file_path.parts):
            continue

        rel = str(file_path.relative_to(root))
        ext = file_path.suffix.lower()
        name_lower = file_path.name.lower()

        # ── Images ────────────────────────────────────────────────
        if ext in IMAGE_EXTENSIONS:
            try:
                if file_path.stat().st_size <= MAX_FILE_SIZE_BYTES:
                    image_files[rel] = file_path.read_bytes()
            except OSError:
                pass
            continue

        # ── Decide whether to read as text ────────────────────────
        is_text = (
            ext in TEXT_EXTENSIONS
            or name_lower in {"manifest.mf", ".project", "makefile", "dockerfile"}
            or (ext == "" and file_path.stat().st_size < 10_000)
        )
        if not is_text:
            continue

        # ── Size guard ────────────────────────────────────────────
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_SIZE_BYTES:
            skipped.append(rel)
            continue

        # ── Read ──────────────────────────────────────────────────
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            content = f"[Could not read file: {exc}]"

        lang = LANG_MAP.get(ext, "")
        block = (
            f"\n### 📄 `{rel}`\n"
            f"```{lang}\n"
            f"{content.strip()}\n"
            f"```\n"
        )

        # ── Context-size guard ────────────────────────────────────
        if total_chars + len(block) > MAX_CONTEXT_CHARS:
            skipped.append(rel)
            continue

        parts.append(block)
        total_chars += len(block)

    # Assemble final context
    header = (
        "## 🗂️ Project Directory Structure\n"
        f"```\n{tree}\n```\n\n"
        "## 📁 File Contents\n"
    )
    footer = ""
    if skipped:
        footer = (
            "\n\n---\n"
            f"⚠️ The following {len(skipped)} file(s) were skipped "
            "(too large or context limit reached):\n"
            + "\n".join(f"  - {s}" for s in skipped)
        )

    context = header + "".join(parts) + footer
    return context, image_files
