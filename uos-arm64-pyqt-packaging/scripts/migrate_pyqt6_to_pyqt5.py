#!/usr/bin/env python3
"""Mechanically migrate PyQt6 source code to PyQt5 + Python 3.7 compatibility.

Part of the uos-arm64-pyqt-packaging skill.

Usage:
    python3 migrate_pyqt6_to_pyqt5.py <src-dir> --dry-run
    python3 migrate_pyqt6_to_pyqt5.py <src-dir> --apply --backup
    python3 migrate_pyqt6_to_pyqt5.py <src-dir> --apply --exclude vendored/foo.py --report report.json

Rules applied:
    1. PyQt6 -> PyQt5 in imports and bare references
    2. Scoped enums (Qt.ItemFlag.X, QMessageBox.StandardButton.Ok, ...) -> flat enums
    3. .exec( -> .exec_(
    4. Insert `from __future__ import annotations` after the module docstring

The script is idempotent and never touches files under third_party/, .git/,
__pycache__/, .venv/ or venv/. Always review the --dry-run report before --apply.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import shutil
import sys
import tokenize
from pathlib import Path

FUTURE_LINE = "from __future__ import annotations\n"

# PyQt6 scoped-enum namespaces. Only these middle segments are collapsed.
ENUM_SCOPES = [
    "ItemFlag", "ItemDataRole", "CheckState", "ContextMenuPolicy",
    "AlignmentFlag", "GlobalColor", "Orientation", "WindowType",
    "KeyboardModifier", "MouseButton", "DropAction", "ToolBarArea",
    "CursorShape", "TextInteractionFlag", "FocusPolicy", "AspectRatioMode",
    "TransformationMode", "ConnectionType", "ApplicationAttribute",
    "WidgetAttribute", "StandardButton", "DialogCode", "SelectionBehavior",
    "EditTrigger", "Filter", "ButtonRole", "Icon", "MoveMode", "SortOrder",
    "Axis", "ItemType", "State", "Shadow", "Shape", "ColorRole", "Key",
    "ShortcutContext", "ToolButtonStyle", "ScrollBarPolicy", "TabPosition",
    "TabShape", "Section", "TextFlag", "TileRule", "FileFlag", "Permission",
]

SCOPE_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\.(" + "|".join(ENUM_SCOPES) + r")"
    r"\.([A-Za-z_][A-Za-z0-9_]*)\b"
)
PYQT6_RE = re.compile(r"\bPyQt6\b")
EXEC_RE = re.compile(r"\.exec\(")
SKIP_DIRS = {"third_party", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".idea", ".vscode"}


def iter_py_files(root: Path, excludes: list[str]):
    ex = [Path(e).as_posix() for e in excludes]
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in Path(rel).parts[:-1]):
            continue
        if any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in ex):
            continue
        yield path, rel


def insert_future_import(source: str) -> tuple[str, list[str]]:
    """Insert the future import after the module docstring / leading comments."""
    if re.search(r"^from __future__ import annotations\s*$", source, re.MULTILINE):
        return source, []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return source, [f"SKIP future-import: file has a syntax error (line {exc.lineno})"]

    lines = source.splitlines(keepends=True)
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        insert_at = body[0].end_lineno  # 1-based line after docstring
    elif body:
        insert_at = body[0].lineno - 1  # 0-based index of first statement
    else:
        insert_at = len(lines)

    # Shebang / encoding declarations / comments legally precede a future import,
    # so inserting immediately before the first statement is always correct.
    lines.insert(insert_at, FUTURE_LINE)
    return "".join(lines), ["insert `from __future__ import annotations`"]


def mask_literals(source: str) -> str:
    """Return a same-length copy with strings/comments blanked out.

    Regexes then match only real code, so UI text and docstrings such as
    'PyQt6-style' are never rewritten. Offsets stay identical to `source`.
    """
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    masked = list(source)
    literal_types = {tokenize.COMMENT, tokenize.STRING}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        literal_types.add(getattr(tokenize, name, -1))
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type not in literal_types:
                continue
            a = offsets[tok.start[0] - 1] + tok.start[1]
            b = offsets[tok.end[0] - 1] + tok.end[1]
            for i in range(a, min(b, len(masked))):
                if masked[i] != "\n":
                    masked[i] = " "
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source  # best effort: fall back to full-text matching
    return "".join(masked)


def transform(source: str) -> tuple[str, list[str]]:
    changes: list[str] = []

    def apply(pattern: re.Pattern, make_replacement) -> None:
        nonlocal source
        masked = mask_literals(source)
        for m in reversed(list(pattern.finditer(masked))):
            replacement, note = make_replacement(m)
            source = source[:m.start()] + replacement + source[m.end():]
            if note:
                changes.append(note)

    def scoped(m: re.Match):
        prefix, member = m.group(1), m.group(3)
        return "%s.%s" % (prefix, member), "enum: %s -> %s.%s" % (m.group(0), prefix, member)

    def pyqt6(m: re.Match):
        return "PyQt5", "PyQt6 -> PyQt5"

    def exec_(m: re.Match):
        return ".exec_(", ".exec( -> .exec_("

    apply(SCOPE_RE, scoped)
    apply(PYQT6_RE, pyqt6)
    apply(EXEC_RE, exec_)

    source, future_changes = insert_future_import(source)
    changes.extend(future_changes)
    return source, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate PyQt6 source to PyQt5 + Python 3.7")
    ap.add_argument("src", help="source directory (work on a COPY of the project)")
    ap.add_argument("--dry-run", action="store_true", help="report only (default)")
    ap.add_argument("--apply", action="store_true", help="write changes back to disk")
    ap.add_argument("--backup", action="store_true", help="keep a .bak copy of each modified file")
    ap.add_argument("--exclude", action="append", default=[], help="relative file path to skip (repeatable)")
    ap.add_argument("--report", help="write a JSON report to this path")
    args = ap.parse_args()

    root = Path(args.src).resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2
    if args.apply and args.dry_run:
        print("ERROR: --apply and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    report: dict = {"src": str(root), "mode": "apply" if args.apply else "dry-run", "files": []}
    total_changes = 0
    total_files = 0
    syntax_errors = 0

    for path, rel in iter_py_files(root, args.exclude):
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            print(f"WARN  {rel}: cannot read ({exc})")
            continue
        new, changes = transform(original)
        if any(c.startswith("SKIP future-import") for c in changes):
            syntax_errors += 1
        if not changes:
            continue
        total_files += 1
        total_changes += len(changes)
        report["files"].append({"path": rel, "changes": changes})
        print(f"{'[APPLY]' if args.apply else '[DRY ]'} {rel}: {len(changes)} change(s)")
        for c in changes[:6]:
            print(f"        - {c}")
        if len(changes) > 6:
            print(f"        ... and {len(changes) - 6} more")
        if args.apply:
            if args.backup:
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            path.write_text(new, encoding="utf-8")

    print()
    print(f"Summary: {total_files} file(s), {total_changes} change(s), "
          f"{syntax_errors} file(s) with pre-existing syntax errors")
    if not args.apply:
        print("Nothing written. Review the report, then re-run with --apply --backup.")
    print("Manual review still required: enum replacements on custom classes, "
          "runtime-position PEP 585/604 generics, QAction import module.")

    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON report: {args.report}")
    return 0 if syntax_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
