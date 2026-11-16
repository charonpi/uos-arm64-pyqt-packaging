#!/usr/bin/env python3
"""Static gate: is this source tree safe to import on CPython 3.7?

Part of the uos-arm64-pyqt-packaging skill.

Checks performed on every .py file (third_party/, .git/, __pycache__/, venv/ skipped):
    - parses with the Python 3.7 grammar (catches :=, f"{x=}", /, match, ...)
    - `from __future__ import annotations` present when annotations are used
    - PEP 585 generics (list[str]) and PEP 604 unions (X | None) only in
      annotation positions, never evaluated at runtime
    - known 3.8+ stdlib APIs (cached_property, math.prod, typing.Protocol, ...)

Usage:
    python3 check_py37_compat.py <src-dir>
    python3 check_py37_compat.py <src-dir> --json report.json
    python3 check_py37_compat.py <src-dir> --strict   # WARN also fails the build

Exit code 0 = no ERROR; 1 = ERROR found (or WARN with --strict); 2 = bad arguments.
Run this with Python 3.8+ (the checker itself); the TARGET code must be 3.7-safe.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

BUILTIN_GENERICS = {"list", "dict", "set", "tuple", "frozenset", "type"}
SKIP_DIRS = {"third_party", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".idea", ".vscode"}
API_38_PATTERNS = [
    (r"cached_property", "functools.cached_property requires Python 3.8"),
    (r"\bmath\.(prod|isqrt|comb|perm|lcm|gcd)\b", "math helper requires Python 3.8+"),
    (r"\btyping\.(Protocol|Literal|Final|TypedDict|runtime_checkable)\b",
     "typing member requires Python 3.8+ (use typing_extensions and vendor it)"),
    (r"\bimportlib\.metadata\b", "importlib.metadata requires Python 3.8"),
    (r"\basyncio\.to_thread\b", "asyncio.to_thread requires Python 3.9"),
    (r"\bzoneinfo\b", "zoneinfo requires Python 3.9 (use pytz and vendor it)"),
    (r"\bgraphlib\b", "graphlib requires Python 3.9"),
    (r"f['\"][^'\"]*\{[A-Za-z_][A-Za-z0-9_]*=\}", "f-string debug specifier requires Python 3.8"),
]
FUTURE_RE = re.compile(r"^from __future__ import .*annotations.*$", re.MULTILINE)


def iter_py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        rel_parts = path.relative_to(root).parts[:-1]
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        yield path, path.relative_to(root).as_posix()


def annotation_node_ids(tree: ast.AST) -> set[int]:
    """All node ids that belong to an annotation subtree (lazily evaluated)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            candidates = list(getattr(a, "posonlyargs", [])) + list(a.args) + list(a.kwonlyargs)
            candidates += [x for x in (a.vararg, a.kwarg) if x is not None]
            anns = [c.annotation for c in candidates if c.annotation is not None]
            if node.returns is not None:
                anns.append(node.returns)
            for ann in anns:
                ids.update(id(n) for n in ast.walk(ann))
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            ids.update(id(n) for n in ast.walk(node.annotation))
    return ids


def parse_with_37(source: str):
    """Return (tree, feature_version, error)."""
    last_value_error = None
    for fv in ((3, 7), (3, 8)):
        try:
            return ast.parse(source, feature_version=fv), fv, None
        except ValueError as exc:  # interpreter does not support this feature_version
            last_value_error = exc
            continue
        except SyntaxError as exc:
            return None, fv, exc
    return None, None, last_value_error or RuntimeError("cannot parse source")


def check_file(path: Path, rel: str) -> list[dict]:
    issues: list[dict] = []
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return [{"file": rel, "line": 0, "level": "WARN", "message": f"cannot read: {exc}"}]

    tree, fv, err = parse_with_37(source)
    if err is not None:
        line = getattr(err, "lineno", 0) or 0
        issues.append({"file": rel, "line": line, "level": "ERROR",
                       "message": f"not valid under Python {fv[0]}.{fv[1]} grammar: {getattr(err, 'msg', err)}"})
        return issues
    if fv != (3, 7):
        issues.append({"file": rel, "line": 0, "level": "WARN",
                       "message": f"interpreter only supports feature_version {fv}; "
                                  "3.8+ syntax not fully detected, verify with real Python 3.7"})

    has_future = bool(FUTURE_RE.search(source))
    ann_ids = annotation_node_ids(tree)

    # Runtime-position PEP 585 / PEP 604 constructs.
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in BUILTIN_GENERICS and id(node) not in ann_ids:
            issues.append({"file": rel, "line": node.lineno, "level": "ERROR",
                           "message": f"runtime-position `{node.value.id}[...]`: Python 3.7 raises "
                                      "TypeError; move it into an annotation"})
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) and id(node) not in ann_ids:
            left_is_type = isinstance(node.left, (ast.Name, ast.Subscript, ast.Constant))
            right_is_type = isinstance(node.right, (ast.Name, ast.Subscript, ast.Constant))
            if left_is_type and right_is_type:
                issues.append({"file": rel, "line": node.lineno, "level": "ERROR",
                               "message": "runtime-position `X | Y` union: Python 3.7 evaluates it; "
                                          "move it into an annotation"})

    uses_annotation = any(isinstance(n, (ast.AnnAssign,)) for n in ast.walk(tree)) or \
        any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and
            (n.returns is not None or any(a.annotation for a in n.args.args)) for n in ast.walk(tree))
    uses_modern = any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                      and n.value.id in BUILTIN_GENERICS for n in ast.walk(tree)) or \
        any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr) for n in ast.walk(tree))
    if not has_future:
        level = "ERROR" if (uses_modern and uses_annotation) else "WARN"
        issues.append({"file": rel, "line": 1, "level": level,
                       "message": "missing `from __future__ import annotations`" +
                                  (" (required: modern generics/unions present)" if level == "ERROR" else "")})

    for pattern, message in API_38_PATTERNS:
        for m in re.finditer(pattern, source):
            line = source.count("\n", 0, m.start()) + 1
            issues.append({"file": rel, "line": line, "level": "WARN", "message": message})

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Python 3.7 import-time compatibility")
    ap.add_argument("src", help="source directory to check")
    ap.add_argument("--json", dest="json_out", help="write a JSON report")
    ap.add_argument("--strict", action="store_true", help="treat WARN as failure")
    args = ap.parse_args()

    root = Path(args.src).resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    all_issues: list[dict] = []
    file_count = 0
    for path, rel in iter_py_files(root):
        file_count += 1
        all_issues.extend(check_file(path, rel))

    errors = [i for i in all_issues if i["level"] == "ERROR"]
    warns = [i for i in all_issues if i["level"] == "WARN"]

    for i in sorted(all_issues, key=lambda x: (x["file"], x["line"])):
        print(f"{i['level']:<5} {i['file']}:{i['line']}  {i['message']}")
    print()
    print(f"Scanned {file_count} file(s): {len(errors)} ERROR, {len(warns)} WARN")
    if errors:
        print("GATE FAILED. Fix every ERROR before building the .deb "
              "(see references/migration-guide.md).")
    elif not warns:
        print("GATE PASSED. Source is safe for CPython 3.7 import.")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"root": str(root), "files": file_count, "issues": all_issues},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON report: {args.json_out}")

    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
