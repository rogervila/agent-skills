---
name: "Typing Equipment Code"
description: "Rules and verified tooling for writing fully type-annotated Equipment code: which types to use for framework services, config values, containers, tasks, and tests, and how to check them with mypy."
tags: [equipment, typing, type-hints, annotations, mypy, py.typed, AbstractLogger, AbstractQueue, AbstractStorage, SQLAlchemyFactory, Mapped, DeclarativeBase, TYPE_CHECKING, create_autospec, disallow-untyped-defs]
---

# Typing Equipment Code

Every function, method, and test you write in an Equipment project must be fully type-annotated, and the annotations must pass a type checker. This file says which types to use and how to check them. Everything here was verified on 2026-11-01 with `equipment` 1.3.0, `dependency-injector` 4.49.1, `SQLAlchemy` 2.1.6, and mypy 2.4.1 on Python 3.15.1.

## Rules

1. Annotate every parameter and every return type, including `-> None`, `__init__`, `setUp`, test methods, queue tasks, scheduler jobs, route handlers, and FastAPI dependencies. `self` and `cls` stay unannotated.
2. Use Python 3.13+ syntax: `list[str]`, `dict[str, Any]`, `str | None`, `collections.abc.Callable` and `Iterator`, and PEP 695 type parameters (`def f[T](...)`) where generics are needed.
3. Annotate injected framework services with Equipment's interfaces, not with the concrete factories, so tests can pass `NullLogger`, mocks, or custom drivers.
4. Give config-derived constructor parameters concrete types (`str`, `int`, `bool`) and make the injected value match: quote string placeholders in YAML and inject numbers with `.as_int()` or `.as_float()`.
5. Do not rebind `app = app()` in new code. Use `application = app()`. The rebinding is a type error (the name changes from a function to a container).
6. Never silence the checker broadly. The one known false positive in generated projects gets a narrow, commented `# type: ignore[arg-type]` (see below).

## Types For Equipment Services

| What you inject or receive | Annotate as | Import |
|---|---|---|
| `application.log()` | `AbstractLogger` | `from equipment.Log.AbstractLogger import AbstractLogger` |
| `application.queue()` | `AbstractQueue` | `from equipment.Queue.AbstractQueue import AbstractQueue` |
| `application.storage()` | `AbstractStorage` | `from equipment.Storage.AbstractStorage import AbstractStorage` |
| `application.database()` | `SQLAlchemyFactory` (there is no abstract database interface) | `from equipment.Database.SQLAlchemyFactory import SQLAlchemyFactory` |
| `application.database().session()` | `Session` | `from sqlalchemy.orm import Session` |
| Scheduler base class | `Scheduler` | `from equipment.Scheduler.Scheduler import Scheduler` |
| The container | `App` | `from app import App` |
| Raw framework config sections (custom factories) | `dict[str, Any]` | `from typing import Any` |

The interfaces are plain `abc.ABC` classes, so importing them is cheap. Use `typing.TYPE_CHECKING` imports when a type is only needed for annotations and importing it at runtime would create a cycle (for example `App` inside a module that `app/__init__.py` imports) or load a heavy library early. The generated `app/Scheduler.py` uses this pattern with quoted annotations:

```python
# Quoted from the generated app/Scheduler.py (Equipment template, main branch)
from typing import TYPE_CHECKING
from equipment.Scheduler.Scheduler import Scheduler as Equipment

if TYPE_CHECKING:
    from equipment.Log.AbstractLogger import AbstractLogger
    from equipment.Queue.AbstractQueue import AbstractQueue
    from app.Inspire import Inspire
```

## What The Checker Infers

With the configuration below, mypy follows `dependency-injector`'s generic provider stubs. Verified `reveal_type` results:

| Expression | Inferred type |
|---|---|
| `app()` | `app.App` |
| `app().inspiring()` | `app.Inspire.Inspire` |
| `app().log()` | `equipment.Log.LoggerFactory.LoggerFactory` |
| `app().storage()` | `equipment.Storage.StorageFactory.StorageFactory` |
| `app().queue()` | `equipment.Queue.QueueFactory.QueueFactory` |
| `app().database()` | `equipment.Database.SQLAlchemyFactory.SQLAlchemyFactory` |
| `app().database().session()` | `sqlalchemy.orm.session.Session` |
| `app().config.app.name()` | `Any` |

Registered services get their real type automatically: `reports = Singleton(Reports, ...)` makes `app().reports()` a `Reports`. Constructor arguments passed to `Singleton(...)` are not checked against the constructor signature, so keep registrations and constructors in sync by reading both.

Config values are `Any`. Convert them where they enter typed code:

```python
port: int = int(application.config.web.port())
debug: bool = str(application.config.app.debug()).lower() == "true"
```

## Typed Service, Registration, Task, And Test

```python
# app/Reports.py
from equipment.Log.AbstractLogger import AbstractLogger
from equipment.Storage.AbstractStorage import AbstractStorage


class Reports:
    def __init__(self, storage: AbstractStorage, log: AbstractLogger, output_path: str) -> None:
        self.storage = storage
        self.log = log
        self.output_path = output_path

    def write_daily_report(self, content: str) -> str:
        if not self.storage.write(self.output_path, content):
            raise RuntimeError("Could not write daily report")
        self.log.info("Daily report written", extra={"path": self.output_path})
        return self.output_path
```

```python
# app/__init__.py
from dependency_injector.providers import ThreadSafeSingleton as Singleton
from equipment import Equipment

from app.Reports import Reports


class App(Equipment):
    reports = Singleton(Reports, Equipment.storage, Equipment.log, Equipment.config.reports.output_path)


def app(base_path: str | None = None) -> App:
    # cachetools.cached under @classmethod confuses mypy's argument check.
    return App.make(base_path)  # type: ignore[arg-type]
```

```python
# app/jobs/reports.py
def write_daily_report(content: str) -> None:
    from app import app  # imported here: app/__init__.py may import this module

    app().reports().write_daily_report(content)
```

```python
# tests/app/test_Reports.py
from unittest.mock import create_autospec

from equipment.Storage.AbstractStorage import AbstractStorage

from tests.TestCase import TestCase


class ReportsTest(TestCase):
    def test_writes_report(self) -> None:
        storage = create_autospec(AbstractStorage, instance=True)
        storage.write.return_value = True
        self.enterContext(self.app.storage.override(storage))
        self.app.reports.reset()
        self.addCleanup(self.app.reports.reset)

        self.assertEqual("reports/daily.txt", self.app.reports().write_daily_report("Ready"))
        storage.write.assert_called_once_with("reports/daily.txt", "Ready")
```

`create_autospec(AbstractStorage, instance=True)` builds a mock that only allows the interface's methods with their signatures, so misspelled or wrongly called methods fail the test. Declare instance attributes of the shared `TestCase` (`app: App`, `fake: Faker`) so tests get typed access; see `references/testing.md`.

## Typed Models

Use SQLAlchemy 2.x typed declarative mapping instead of untyped `Column` attributes:

```python
# app/models.py
from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLite only auto-increments INTEGER primary keys; keep BIGINT elsewhere.
BigId = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    completed: Mapped[bool]
```

`Mapped[str]` means `NOT NULL`; use `Mapped[str | None]` for nullable columns. See `references/database.md` for the SQLite primary-key detail.

## Checking Types

### Why The Default Command Fails

Verified on a fresh project:

| Command | Result |
|---|---|
| `python -m mypy app tests` | `app/Scheduler.py: error: Source file found twice under different module names: "demo.app.Scheduler" and "app.Scheduler"`. The template has an `__init__.py` in the project root. |
| `python -m mypy --explicit-package-bases app tests` | `error: Skipping analyzing "equipment": module is installed, but missing library stubs or py.typed marker  [import-untyped]`. Equipment ships type hints but no `py.typed`, so its types become `Any`. |
| `python -m mypy --explicit-package-bases --follow-untyped-imports app tests` | Works. One template error remains: `app/__init__.py:19: error: Argument 1 to "__call__" of "_cached_wrapper" has incompatible type "str | None"; expected "type[Equipment]"  [arg-type]`. |

The last error is a false positive: `Equipment.make()` stacks `cachetools.cached` under `@classmethod`. Silence only that line, with a reason, as in the `app/__init__.py` example above.

The template's entry points (`main.py`, `web.py`, `scheduler.py`, `queues.py`) rebind `app = app()` and fail the check. Leave them out of the checked files, or rename the variable to `application` when you edit one.

### Project Configuration

Add this to the generated `pyproject.toml` so `python -m mypy` works without flags (verified):

```toml
[tool.mypy]
python_version = "3.13"
files = ["app", "tests"]
explicit_package_bases = true
follow_untyped_imports = true
```

Add entry points to `files` once they no longer rebind `app`. Keep `database/migrations/` out: `env.py` uses the untyped `parent_import` package.

mypy is not in the generated `dev` extra. To check your work, install it in the project's virtual environment (`python -m pip install mypy`), and propose adding it to `[project.optional-dependencies] dev` together with the `[tool.mypy]` block. Ask before committing new dependencies.

### Commands

```bash
# Whole project: type errors anywhere in app/ and tests/
python -m mypy --explicit-package-bases --follow-untyped-imports app tests

# Files you wrote or changed: also require complete annotations
python -m mypy --explicit-package-bases --follow-untyped-imports \
  --follow-imports=silent --disallow-untyped-defs --disallow-incomplete-defs \
  app/Reports.py app/jobs/reports.py tests/app/test_Reports.py
```

`--follow-imports=silent` still analyzes imported modules but only reports errors in the files you list. That keeps pre-existing, partially typed template code (for example `tests/app/test_Inspire.py`, whose test methods have no `-> None`) from failing your check, while every file you wrote must be fully annotated. Verified: all typed examples in this skill pass the strict command, and `tests/app/test_Inspire.py` fails it with `Function is missing a return type annotation  [no-untyped-def]`.

With the `[tool.mypy]` block in place, the shorter forms work too:

```bash
python -m mypy
python -m mypy --follow-imports=silent --disallow-untyped-defs --disallow-incomplete-defs app/Reports.py
```

## Typing Tasks, Jobs, And Routes

- Queue tasks take small, serializable, typed arguments and return `None`: `def rebuild_report(report_id: int) -> None`.
- Scheduler jobs registered with `self.schedule.every(...).do(...)` are typed functions or bound methods; decorators that wrap them use `ParamSpec`, for example `def safe_job[**P](log: AbstractLogger) -> Callable[[Callable[P, object]], Callable[P, None]]` (see `references/scheduler.md`).
- FastAPI handlers declare parameter and response types; use `Annotated[Session, Depends(get_session)]` for dependencies (see `references/fastapi.md`).
- Values written to storage are strings. Give structured payloads a `TypedDict` or a dataclass, then serialize them explicitly with `json.dumps`.

## Best Practices

- Annotate everything you write, including `-> None`, and keep annotations true at runtime by quoting string placeholders and using `.as_int()` for numbers.
- Depend on `AbstractLogger`, `AbstractQueue`, and `AbstractStorage`; use `SQLAlchemyFactory` and `Session` for the database.
- Use `create_autospec(Interface, instance=True)` for mocks of framework services.
- Use SQLAlchemy `DeclarativeBase` and `Mapped[...]` for models.
- Check with `--explicit-package-bases --follow-untyped-imports`, and run the strict flags on every file you touched.
- Silence only the known `App.make` false positive, with a comment; fix every other error.
