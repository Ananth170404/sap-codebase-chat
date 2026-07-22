"""Unit tests for file_processor.py — pure filesystem logic, no Streamlit/API deps."""

from __future__ import annotations

import pytest

import file_processor as fp

# ─────────────────────────────────────────────────────────────────
# build_directory_tree
# ─────────────────────────────────────────────────────────────────


def test_build_directory_tree_root_name(tmp_path):
    tree = fp.build_directory_tree(str(tmp_path))
    assert tree.splitlines()[0] == f"{tmp_path.name}/"


def test_build_directory_tree_lists_files_and_dirs(tmp_path):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("print(2)")

    tree = fp.build_directory_tree(str(tmp_path))

    assert "a.py" in tree
    assert "sub" in tree
    assert "b.py" in tree


def test_build_directory_tree_dirs_listed_before_files(tmp_path):
    (tmp_path / "z_file.txt").write_text("x")
    (tmp_path / "a_dir").mkdir()

    tree = fp.build_directory_tree(str(tmp_path))
    lines = tree.splitlines()

    assert lines.index("├── a_dir") < lines.index("└── z_file.txt")


@pytest.mark.parametrize("skip_name", sorted(fp.SKIP_NAMES))
def test_build_directory_tree_skips_ignored_names(tmp_path, skip_name):
    (tmp_path / skip_name).mkdir()
    (tmp_path / "keep.py").write_text("print(1)")

    tree = fp.build_directory_tree(str(tmp_path))

    assert skip_name not in tree
    assert "keep.py" in tree


def test_build_directory_tree_nested_indentation(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested").mkdir()
    (tmp_path / "sub" / "nested" / "deep.py").write_text("x")

    tree = fp.build_directory_tree(str(tmp_path))

    assert "deep.py" in tree
    deep_line = next(line for line in tree.splitlines() if "deep.py" in line)
    assert deep_line.startswith("        ")  # nested two levels deep


# ─────────────────────────────────────────────────────────────────
# get_file_type_summary
# ─────────────────────────────────────────────────────────────────


def test_get_file_type_summary_counts_by_extension(tmp_path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.py").write_text("x")
    (tmp_path / "c.md").write_text("x")

    summary = fp.get_file_type_summary(str(tmp_path))

    assert summary[".py"] == 2
    assert summary[".md"] == 1


def test_get_file_type_summary_counts_nested_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "d.js").write_text("x")

    summary = fp.get_file_type_summary(str(tmp_path))

    assert summary[".js"] == 1


def test_get_file_type_summary_ignores_skip_dirs(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_text("x")
    (tmp_path / "real.py").write_text("x")

    summary = fp.get_file_type_summary(str(tmp_path))

    assert ".pyc" not in summary
    assert summary[".py"] == 1


def test_get_file_type_summary_handles_extensionless_files(tmp_path):
    (tmp_path / "Makefile").write_text("x")

    summary = fp.get_file_type_summary(str(tmp_path))

    assert summary[""] == 1


# ─────────────────────────────────────────────────────────────────
# build_codebase_context
# ─────────────────────────────────────────────────────────────────


def test_build_codebase_context_includes_text_file_contents(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    context, images = fp.build_codebase_context(str(tmp_path))

    assert "main.py" in context
    assert "print('hello')" in context
    assert images == {}


def test_build_codebase_context_skips_unknown_extensions(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")

    context, _ = fp.build_codebase_context(str(tmp_path))

    # The name still shows up in the directory tree header; it must not get
    # a fenced content block in the File Contents section.
    file_contents_section = context.split("## \U0001f4c1 File Contents", 1)[1]
    assert "data.bin" not in file_contents_section


def test_build_codebase_context_collects_images_as_bytes(tmp_path):
    img_bytes = b"\x89PNG\r\n\x1a\n"
    (tmp_path / "logo.png").write_bytes(img_bytes)

    context, images = fp.build_codebase_context(str(tmp_path))

    assert images["logo.png"] == img_bytes
    # Images are returned separately, not inlined as a fenced content block.
    file_contents_section = context.split("## \U0001f4c1 File Contents", 1)[1]
    assert "logo.png" not in file_contents_section


def test_build_codebase_context_skips_files_over_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(fp, "MAX_FILE_SIZE_BYTES", 10)
    (tmp_path / "big.py").write_text("x" * 100)

    context, _ = fp.build_codebase_context(str(tmp_path))

    assert "x" * 100 not in context
    assert "big.py" in context  # still reported in the skipped footer
    assert "skipped" in context.lower()


def test_build_codebase_context_respects_context_char_limit(tmp_path, monkeypatch):
    (tmp_path / "aaa_first.py").write_text("x" * 20)
    (tmp_path / "zzz_second.py").write_text("y" * 20)

    # Compute the exact block the first file produces so the limit can be
    # pinned precisely: just enough room for file 1, none left for file 2.
    lang = fp.LANG_MAP.get(".py", "")
    block1 = f"\n### \U0001f4c4 `aaa_first.py`\n```{lang}\n{'x' * 20}\n```\n"
    monkeypatch.setattr(fp, "MAX_CONTEXT_CHARS", len(block1))

    context, _ = fp.build_codebase_context(str(tmp_path))

    assert "x" * 20 in context
    assert "y" * 20 not in context
    assert "zzz_second.py" in context  # listed in the skipped footer


def test_build_codebase_context_skips_git_directory_contents(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret-token")
    (tmp_path / "app.py").write_text("print(1)")

    context, _ = fp.build_codebase_context(str(tmp_path))

    assert "secret-token" not in context
    assert "app.py" in context


def test_build_codebase_context_includes_directory_tree_header(tmp_path):
    (tmp_path / "app.py").write_text("print(1)")

    context, _ = fp.build_codebase_context(str(tmp_path))

    assert "Project Directory Structure" in context
    assert "File Contents" in context
