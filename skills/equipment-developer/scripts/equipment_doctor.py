#!/usr/bin/env python3
"""Read-only checks for known pitfalls in Equipment-generated projects.

Usage:
    python equipment_doctor.py [PROJECT_DIR]

The script never imports or executes project code. It reads files as text and
parses Python with the standard library ``ast`` module. It needs Python 3.8+
and no third-party packages.

Exit codes:
    0  no warnings (info findings may still be printed)
    1  at least one warning
    2  PROJECT_DIR is not an Equipment project or cannot be read

Every check is explained in references/verified-behavior.md of the
equipment-developer skill.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

# Directories that never contain project source worth parsing.
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", "env", "node_modules",
    "__pycache__", "build", "dist", "site-packages", ".mypy_cache", ".pytest_cache",
    "htmlcov", ".eggs",
}

# Directories `equipment compile` skips (equipment/Command/CompileCommand.py).
COMPILE_IGNORED_DIRS = {"__pycache__", "dist", "tests", "equipment"}

FRAMEWORK_PROVIDERS = {"log", "queue", "storage", "database"}

# Files where a test command is commonly written down.
COMMAND_FILE_GLOBS = [
    "README.md", "README.rst", "Makefile", "tox.ini", "noxfile.py", "setup.cfg",
    "pyproject.toml", ".gitlab-ci.yml", "*.sh", "*.bat", "*.ps1",
    ".github/workflows/*.yml", ".github/workflows/*.yaml",
]

DRIVERS = {
    # DB_CONNECTION: (default dialect in config/database.yaml, accepted packages)
    "mysql": ("mysql+mysqlconnector", ("mysql-connector-python",)),
    "postgresql": ("postgresql+psycopg2", ("psycopg2-binary", "psycopg2")),
}


@dataclass
class Finding:
    level: str  # "warning" or "info"
    code: str
    path: str
    message: str
    fix: str


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._env: Optional[Dict[str, str]] = None

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def read_text(self, relative: str) -> Optional[str]:
        path = self.root / relative
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @property
    def env(self) -> Dict[str, str]:
        """Values from the project's .env file (not the current process environment)."""
        if self._env is None:
            self._env = parse_env(self.read_text(".env") or "")
        return self._env

    def python_files(self) -> Iterator[Path]:
        for directory, dirnames, filenames in os.walk(self.root):
            current = Path(directory)
            dirnames[:] = sorted(
                name for name in dirnames
                if name not in SKIP_DIRS and not (current / name / "pyvenv.cfg").is_file()
            )
            for filename in sorted(filenames):
                if filename.endswith(".py"):
                    yield current / filename


def parse_env(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


def is_unset(value: Optional[str]) -> bool:
    return value is None or value.strip() in ("", "null", "None")


def parse_python(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return None


def is_equipment_project(root: Path) -> bool:
    init = root / "app" / "__init__.py"
    if not init.is_file() or not (root / "config").is_dir():
        return False
    try:
        return "Equipment" in init.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


# --------------------------------------------------------------------------
# Testing checks
# --------------------------------------------------------------------------

def check_test_shadowing(project: Project) -> List[Finding]:
    tests = project.root / "tests"
    if not tests.is_dir():
        return []

    shadowed = []
    for child in sorted(tests.iterdir()):
        if not (child.is_dir() and (child / "__init__.py").is_file()):
            continue
        name = child.name
        if (project.root / name / "__init__.py").is_file() or (project.root / f"{name}.py").is_file():
            shadowed.append(name)

    # Info only: harmless while the team runs `python -m unittest`. EQ002 flags commands that break.
    findings = [
        Finding(
            "info", "EQ001", f"tests/{name}/__init__.py",
            f"`python -m unittest discover -s tests` puts tests/ first on sys.path, so tests/{name}/ "
            f"shadows the project's `{name}` package and test imports fail.",
            "Run `python -m unittest` or `python -m unittest discover -s tests -t .` from the project root.",
        )
        for name in shadowed
    ]
    if shadowed:
        findings.extend(find_failing_discover_commands(project))
    return findings


def find_failing_discover_commands(project: Project) -> List[Finding]:
    start_dir = re.compile(r"(?:^|\s)(?:-s|--start-directory)[ =]+[\"']?\.?[\\/]?tests[\\/]?[\"']?(?:\s|$)")
    top_level = re.compile(r"(?:^|\s)(?:-t|--top-level-directory)[ =]")

    seen = set()
    findings = []
    for pattern in COMMAND_FILE_GLOBS:
        for path in sorted(project.root.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if "unittest" in line and "discover" in line and start_dir.search(line) and not top_level.search(line):
                    findings.append(Finding(
                        "warning", "EQ002", f"{project.rel(path)}:{number}",
                        "This command uses `discover -s tests` without `-t .` and fails while a test package "
                        "shadows a project package (see EQ001).",
                        "Replace it with `python -m unittest` or add `-t .`.",
                    ))
    return findings


def check_coveragerc(project: Project) -> List[Finding]:
    text = project.read_text(".coveragerc")
    if text is None:
        return []
    for number, line in enumerate(text.splitlines(), start=1):
        tokens = re.split(r"[\s,=]+", line.strip())
        if "*tests*" in tokens:
            return [Finding(
                "info", "EQ003", f".coveragerc:{number}",
                "With coverage 7 file patterns, `*` does not match `/`, so `*tests*` does not omit tests/ files. "
                "`coverage report` may also fail on dependency-injector's `providers.pyx`.",
                "Use `omit = */tests/*` and `*.pyx` (or run `coverage report --omit=\"*/tests/*,*.pyx\"`).",
            )]
    return []


# --------------------------------------------------------------------------
# Configuration and database checks
# --------------------------------------------------------------------------

def check_env_profile(project: Project) -> List[Finding]:
    if project.env.get("APP_ENV", "").lower() == "production":
        return [Finding(
            "info", "EQ010", ".env",
            "APP_ENV=production. `equipment new` copies .env.example, which uses production values.",
            "Use APP_ENV=local for local development; set production values in the deployment environment.",
        )]
    return []


def check_sqlite_database_name(project: Project) -> List[Finding]:
    env = project.env
    connection = env.get("DB_CONNECTION") or ""
    if is_unset(connection):
        # Without an .env value, config/database.yaml's default decides.
        config = project.read_text("config/database.yaml") or ""
        connection = "sqlite" if re.search(r"\$\{DB_CONNECTION:sqlite\}", config) else ""
    if connection.lower() != "sqlite":
        return []
    database = env.get("DB_DATABASE") or ""
    if is_unset(database) or database == ":memory:":
        return []
    if "/" in database or "\\" in database or "." in database:
        return []
    return [Finding(
        "warning", "EQ011", ".env",
        f"DB_CONNECTION=sqlite with DB_DATABASE={database} creates a SQLite file named `{database}` "
        "in the project root.",
        "Set DB_DATABASE=database/database.sqlite (or remove it to use the config default).",
    )]


def check_database_driver(project: Project) -> List[Finding]:
    connection = project.env.get("DB_CONNECTION", "").lower()
    if connection not in DRIVERS:
        return []
    dialect, packages = DRIVERS[connection]
    config = project.read_text("config/database.yaml") or ""
    if dialect not in config:
        return []
    pyproject = project.read_text("pyproject.toml") or ""
    declared = [
        line for line in pyproject.splitlines()
        if not line.strip().startswith("#") and any(re.search(rf"[\"']{re.escape(p)}\b", line) for p in packages)
    ]
    if declared:
        return []
    return [Finding(
        "warning", "EQ012", ".env",
        f"DB_CONNECTION={connection} uses the `{dialect}` dialect, but pyproject.toml does not declare "
        f"{' or '.join(packages)}. Unless the driver is installed another way, `app.database()` and Alembic "
        "fail with ModuleNotFoundError, and fresh installs will miss it.",
        f"Add `{packages[0]}` to the project dependencies, or use DB_CONNECTION=sqlite with "
        "DB_DATABASE=database/database.sqlite for local work.",
    )]


def check_alembic_metadata(project: Project) -> List[Finding]:
    text = project.read_text("database/migrations/env.py")
    if text is None:
        return []
    for number, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*target_metadata\s*=\s*None\s*(#.*)?$", line):
            return [Finding(
                "info", "EQ020", f"database/migrations/env.py:{number}",
                "target_metadata is None, so `alembic revision --autogenerate` fails.",
                "Import your declarative Base and set `target_metadata = Base.metadata`.",
            )]
    return []


def check_storage_local_key(project: Project) -> List[Finding]:
    text = project.read_text("config/storage.yaml")
    if text is None:
        return []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)local:\s*(#.*)?$", line)
        if not match:
            continue
        indent = len(match.group(1))
        keys: Dict[str, int] = {}
        for offset, child in enumerate(lines[index + 1:], start=index + 2):
            if not child.strip() or child.strip().startswith("#"):
                continue
            child_indent = len(child) - len(child.lstrip())
            if child_indent <= indent:
                break
            key = child.strip().split(":", 1)[0]
            keys.setdefault(key, offset)
        if "root" in keys and "path" not in keys:
            return [Finding(
                "warning", "EQ060", f"config/storage.yaml:{keys['root']}",
                "The local storage disk uses `root`, but Equipment reads `path`.",
                "Rename `root:` to `path:`.",
            )]
    return []


def check_log_directories(project: Project) -> List[Finding]:
    text = project.read_text("config/log.yaml")
    if text is None:
        return []
    findings = []
    seen = set()
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*filename:\s*['\"]?([^'\"#]+?)['\"]?\s*(#.*)?$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if "${" in value:
            continue
        target = Path(value)
        parent = target.parent if target.is_absolute() else (project.root / target).parent
        if parent in seen:
            continue
        seen.add(parent)
        if not parent.is_dir():
            findings.append(Finding(
                "warning", "EQ080", f"config/log.yaml:{number}",
                f"Log directory `{project.rel(parent)}` does not exist. File channels using it raise "
                "FileNotFoundError (sqlite channel: sqlite3.OperationalError), which also breaks queue, storage, "
                "and database creation.",
                "Create the directory (and keep it in Git with a .gitignore), or change the filename.",
            ))
    return findings


# --------------------------------------------------------------------------
# Python source checks (AST only)
# --------------------------------------------------------------------------

def _calls(tree: ast.AST, attribute: str) -> Iterator[ast.Call]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attribute:
            yield node


def check_python_sources(project: Project) -> List[Finding]:
    findings: List[Finding] = []
    uses_push_at: List[str] = []

    for path in project.python_files():
        tree = parse_python(path)
        if tree is None:
            continue
        relative = project.rel(path)
        # Tests usually run the sync driver, where lambdas are fine.
        in_tests = relative.startswith("tests/")

        for call in _calls(tree, "push"):
            if not in_tests and call.args and isinstance(call.args[0], ast.Lambda):
                findings.append(_lambda_finding(relative, call))
        for call in _calls(tree, "push_at"):
            if in_tests:
                continue
            uses_push_at.append(f"{relative}:{call.lineno}")
            if len(call.args) > 1 and isinstance(call.args[1], ast.Lambda):
                findings.append(_lambda_finding(relative, call))

        if relative == "app/__init__.py":
            findings.extend(check_provider_overrides(relative, tree))
        if relative.startswith("app/"):
            findings.extend(check_scheduler_config(relative, tree))

    findings.extend(check_worker(project, uses_push_at))
    return findings


def _lambda_finding(relative: str, call: ast.Call) -> Finding:
    return Finding(
        "warning", "EQ032", f"{relative}:{call.lineno}",
        "A lambda is queued. With QUEUE_CONNECTION=redis it is enqueued (push() returns True, or False if "
        "defined in a __main__ script) and then fails in the worker, which cannot import lambdas.",
        "Queue a module-level function from an importable module under app/.",
    )


def check_provider_overrides(relative: str, tree: ast.AST) -> List[Finding]:
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        overridden = set()
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id in FRAMEWORK_PROVIDERS:
                        overridden.add(target.id)
        if not overridden:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            for inner in ast.walk(statement.value):
                if (
                    isinstance(inner, ast.Attribute)
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "Equipment"
                    and inner.attr in overridden
                ):
                    findings.append(Finding(
                        "warning", "EQ040", f"{relative}:{inner.lineno}",
                        f"`{node.name}` overrides the `{inner.attr}` provider, but this provider still references "
                        f"`Equipment.{inner.attr}` and receives a separate base instance.",
                        f"Reference the overriding provider by its local name: `{inner.attr}`.",
                    ))
    return findings


def check_scheduler_config(relative: str, tree: ast.AST) -> List[Finding]:
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "equipment.Scheduler.Scheduler":
            for name in node.names:
                if name.name == "Scheduler":
                    aliases.add(name.asname or name.name)
    if not aliases:
        return []

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(isinstance(base, ast.Name) and base.id in aliases for base in node.bases):
            continue
        reads, assigned = [], False
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Attribute)
                and inner.attr == "config"
                and isinstance(inner.value, ast.Name)
                and inner.value.id == "self"
            ):
                if isinstance(inner.ctx, ast.Store):
                    assigned = True
                else:
                    reads.append(inner.lineno)
        if reads and not assigned:
            findings.append(Finding(
                "warning", "EQ041", f"{relative}:{reads[0]}",
                f"`{node.name}` reads `self.config`, but Equipment's Scheduler only sets `log`, `schedule`, "
                "and `should_exit`; this raises AttributeError.",
                "Inject the config values through the constructor (for example Equipment.config.app.env).",
            ))
    return findings


def check_worker(project: Project, uses_push_at: List[str]) -> List[Finding]:
    path = project.root / "queues.py"
    tree = parse_python(path) if path.is_file() else None

    findings = []
    work_calls = list(_calls(tree, "work")) if tree is not None else []
    if uses_push_at and work_calls and not any(
        any(keyword.arg == "with_scheduler" for keyword in call.keywords) for call in work_calls
    ):
        findings.append(Finding(
            "warning", "EQ030", f"queues.py:{work_calls[0].lineno}",
            "The worker does not start the RQ scheduler, so jobs from push_at() never run with Redis "
            f"(push_at used at {', '.join(uses_push_at[:3])}).",
            "Call `w.work(with_scheduler=True)`.",
        ))

    env = project.env
    if is_unset(env.get("REDIS_PASSWORD")) and is_unset(env.get("REDIS_USERNAME")):
        return findings

    worker_ignores = tree is not None and any(
        not any(keyword.arg in ("password", "username") for keyword in call.keywords)
        for call in ast.walk(tree)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "Redis"
    )
    container = parse_python(project.root / "app" / "__init__.py")
    queue_overridden = container is not None and any(
        isinstance(target, ast.Name) and target.id == "queue"
        for node in ast.walk(container) if isinstance(node, ast.Assign)
        for target in node.targets
    )
    ignored_by = []
    if not queue_overridden:
        ignored_by.append("Equipment's RedisQueue (no `queue` override in app/__init__.py)")
    if worker_ignores:
        ignored_by.append("queues.py")
    if ignored_by:
        findings.append(Finding(
            "warning", "EQ031", ".env",
            "REDIS_USERNAME/REDIS_PASSWORD are set but ignored by " + " and ".join(ignored_by)
            + ". Pushes fail with AuthenticationError against a protected Redis.",
            "Override the queue provider with an authenticated factory and pass username/password in queues.py "
            "(see references/queue.md).",
        ))
    return findings


# --------------------------------------------------------------------------
# Compilation checks
# --------------------------------------------------------------------------

def check_compile_inputs(project: Project) -> List[Finding]:
    findings = []
    for child in sorted(project.root.iterdir()):
        if not child.is_dir() or child.name in COMPILE_IGNORED_DIRS:
            continue
        if (child / "pyvenv.cfg").is_file() or child.name in ("build", ".tox", ".nox"):
            findings.append(Finding(
                "info", "EQ050", f"{child.name}/",
                f"`equipment compile` would walk `{child.name}/` and compile every .py file in it into the output.",
                "Keep virtual environments outside the project, delete build output first, "
                "or compile from a clean copy.",
            ))
    return findings


CHECKS = [
    check_test_shadowing,
    check_coveragerc,
    check_env_profile,
    check_sqlite_database_name,
    check_database_driver,
    check_alembic_metadata,
    check_storage_local_key,
    check_log_directories,
    check_python_sources,
    check_compile_inputs,
]


def run_checks(root: Path) -> List[Finding]:
    project = Project(root)
    findings: List[Finding] = []
    for check in CHECKS:
        findings.extend(check(project))
    order = {"warning": 0, "info": 1}
    return sorted(findings, key=lambda f: (order.get(f.level, 2), f.code, f.path))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only checks for known pitfalls in Equipment-generated projects.",
    )
    parser.add_argument("project_dir", nargs="?", default=".", help="Project root (default: current directory).")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    if not is_equipment_project(root):
        print(
            f"error: {root} does not look like an Equipment project "
            "(expected app/__init__.py using Equipment and a config/ directory)",
            file=sys.stderr,
        )
        return 2

    findings = run_checks(root)
    print(f"Equipment doctor: {root}")
    print("Read-only: project files were parsed, not imported or executed.")
    if not findings:
        print("No known pitfalls found.")
        return 0

    for finding in findings:
        print()
        print(f"[{finding.level.upper()}] {finding.code} {finding.path}")
        print(f"  {finding.message}")
        print(f"  Fix: {finding.fix}")

    warnings = sum(1 for f in findings if f.level == "warning")
    infos = len(findings) - warnings
    print()
    print(f"Summary: {warnings} warning(s), {infos} info finding(s).")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
