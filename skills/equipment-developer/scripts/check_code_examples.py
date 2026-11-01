#!/usr/bin/env python3
"""Check that the Python examples in this skill are valid and fully type-annotated.

Usage:
    python check_code_examples.py [SKILL_DIR]

Scans SKILL.md and references/*.md for ```python blocks. Every block must parse.
Every function in a block must annotate all parameters (except a leading
self/cls) and its return type, and no block may rebind `app = app()`.

Blocks whose first line starts with `# Quoted from` reproduce upstream Equipment
code verbatim and are exempt from the annotation rules (they must still parse).

Exit codes: 0 = all examples pass, 1 = problems found, 2 = bad arguments.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Union

QUOTE_MARKER = "# Quoted from"
FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


@dataclass
class Block:
    path: Path
    line: int  # 1-based line of the first code line
    code: str

    @property
    def quoted(self) -> bool:
        first = next((line.strip() for line in self.code.splitlines() if line.strip()), "")
        return first.startswith(QUOTE_MARKER)


def python_blocks(path: Path) -> Iterator[Block]:
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        if re.match(r"^\s*```python\s*$", lines[index]):
            start = index + 1
            end = start
            while end < len(lines) and not re.match(r"^\s*```\s*$", lines[end]):
                end += 1
            yield Block(path, start + 1, "\n".join(lines[start:end]))
            index = end
        index += 1


def _unannotated_parameters(node: FunctionNode, is_method: bool) -> List[str]:
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    if is_method and positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]
    missing = [arg.arg for arg in [*positional, *arguments.kwonlyargs] if arg.annotation is None]
    if arguments.vararg is not None and arguments.vararg.annotation is None:
        missing.append(f"*{arguments.vararg.arg}")
    if arguments.kwarg is not None and arguments.kwarg.annotation is None:
        missing.append(f"**{arguments.kwarg.arg}")
    return missing


def check_tree(tree: ast.AST) -> List[str]:
    problems: List[str] = []

    def visit(node: ast.AST, in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                missing = _unannotated_parameters(child, in_class)
                if missing:
                    problems.append(f"line {child.lineno}: `{child.name}` has unannotated parameters: {', '.join(missing)}")
                if child.returns is None:
                    problems.append(f"line {child.lineno}: `{child.name}` has no return annotation")
                visit(child, False)
            elif isinstance(child, ast.ClassDef):
                visit(child, True)
            else:
                visit(child, in_class)

    visit(tree, False)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "app" for target in node.targets)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "app"
        ):
            problems.append(f"line {node.lineno}: `app = app()` rebinds the factory; use `application = app()`")
    return problems


def check_block(block: Block) -> List[str]:
    try:
        tree = ast.parse(block.code)
    except SyntaxError as error:
        return [f"line {(error.lineno or 1)}: does not parse: {error.msg}"]
    if block.quoted:
        return []
    return check_tree(tree)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill_dir", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)

    root = Path(args.skill_dir)
    files = [root / "SKILL.md", *sorted((root / "references").glob("*.md"))]
    if not files[0].is_file():
        print(f"error: {files[0]} not found", file=sys.stderr)
        return 2

    failures = 0
    checked = 0
    quoted = 0
    for path in files:
        for block in python_blocks(path):
            checked += 1
            quoted += block.quoted
            for problem in check_block(block):
                failures += 1
                relative = path.relative_to(root).as_posix()
                print(f"{relative}:{block.line}: {problem}")

    print(f"Checked {checked} Python example(s) ({quoted} quoted upstream); {failures} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
