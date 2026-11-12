---
name: "Verified Behavior And Doc Gaps"
description: "Dated list of Equipment behaviors verified by running a generated project or reading the framework source, including every place where the docs and the actual behavior differ, with fixes."
tags: [equipment, verified, errata, gotchas, pitfalls, doc-gaps, troubleshooting, unittest, coverage, configuration, redis, scheduler, storage, compile, cli, alembic]
---

# Verified Behavior And Doc Gaps

The docs describe intended usage. This file records what the code actually does, so agents do not repeat a broken example or miss a silent failure.

## Verification Environment

- Date: 2026-11-01.
- `equipment` 1.3.0 from PyPI. Identical to `main` at commit `ba2dd07` except for PEP 810 `__lazy_modules__` lines.
- Template: downloaded by `equipment new demo` from the `main` branch on that date.
- Python 3.15.1 on Linux for all probes; the test-discovery failure was also reproduced on Python 3.13.17.
- Library versions in the generated project: `dependency-injector` 4.49.1, `SQLAlchemy` 2.1.6, `rq` 2.12.0, `redis` 8.1.0, `schedule` 1.2.2, `python-json-logger` 4.2.0, `coverage` 7.17.0, `fastapi` 0.162.0, `alembic` 1.20.1. Redis 7.4 ran in Docker for queue checks. Type checks used mypy 2.4.1.
- Not verified: native Windows and macOS behavior.

Evidence types: **Run** means reproduced by executing code; **Source** means read from the framework or template source.

## Testing

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `python -m unittest discover -s tests` runs the generated tests. | Fails: `ImportError: cannot import name 'app' from 'app' (.../tests/app/__init__.py)`. `tests/` becomes the top-level dir and `tests/app/` shadows `app`. | `python -m unittest` or `python -m unittest discover -s tests -t .` | Run (3.13, 3.15) |
| `.coveragerc` `omit = *tests*` omits tests. | Tests are still measured; coverage 7 `*` does not cross `/`. | `omit = */tests/*` | Run |
| `coverage report` works after `coverage run`. | Exits 1: `No source for code: '.../src/dependency_injector/providers.pyx'`. `coverage erase` does not help. | `--omit="*/tests/*,*.pyx"` or `report -i` | Run |
| Each `TestCase` gets a fresh app. | `app()` is cached per base path; overrides and `from_value()` changes leak to later tests. | `enterContext(provider.override(...))`, `enterContext(config.x.override(...))`, `reset_singletons()` | Run |
| `provider.override(mock)` used as a context manager returns the mock. | `__enter__` returns a `providers.Object` wrapper. | Keep your own reference to the mock. | Run |
| Patching `time.sleep` makes scheduler tests instant. | The module did `from time import sleep`; the test still sleeps 1.00 s. | Patch `equipment.Scheduler.Scheduler.sleep`. | Run |
| `faker` is available after `pip install .`. | `faker` is only in the `dev` extra. | `pip install ".[dev]"` | Source |

## Configuration

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| Environment values load as strings. | YAML types substituted values: `8000` int, `false` bool, `yes` True, `null` None, `00123` octal 83. JSON keeps JSON types; INI gives strings. | Quote placeholders that must stay text; cast or use `.as_int()`. | Run |
| A missing config key is an error. | Missing keys return `None` silently. | `.required()` when injecting. | Run |
| Any key name works. | Names such as `from_env`, `override`, `required`, `as_int`, `update`, `provided` resolve to methods. | Avoid those names. | Run |
| `.env` sets the values. | Existing process variables win over `.env`; `.env` values are exported to `os.environ`. | Inspect the real environment. | Run |
| Generated project defaults to SQLite and `APP_ENV=local`. | Generated `.env` (copied from `.env.example`) sets `APP_ENV=production`, `DB_CONNECTION=mysql`, `DB_DATABASE=equipment`. | Edit `.env` after `equipment new`. | Run |
| Running a script from anywhere works. | Base path is the working directory; from elsewhere: `TypeError: 'NoneType' object is not subscriptable`. | Run from the project root or pass `app(base_path)`. | Run |
| `config.override({...})` changes a few keys. | Replaces the whole tree; other keys read `None`. | Override single options. | Run |

## Dependency Injection

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `app()` returns an `App` instance. | Returns a `DynamicContainer`; `isinstance(app(), App)` is `False`. | Do not use `isinstance` on containers. | Run |
| `app()` and `app(os.getcwd())` are the same. | Different cache keys, so two containers with separate singletons. | Call `app()` the same way everywhere. | Run |
| Overriding `queue` in `App` affects all services. | Providers that reference `Equipment.queue` get a separate base instance. | Reference the overriding provider by its local name. | Run |
| Overriding a dependency affects existing services. | Singletons keep what they captured at creation. | `provider.reset()` or `reset_singletons()`. | Run |

## Typing

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `python -m mypy app tests` works on a generated project. | Fails: `Source file found twice under different module names: "demo.app.Scheduler" and "app.Scheduler"` (the template has a root `__init__.py`). | `--explicit-package-bases` | Run |
| Equipment's type hints are visible to checkers. | `equipment` ships no `py.typed`: `Skipping analyzing "equipment": module is installed, but missing library stubs or py.typed marker  [import-untyped]`. | `--follow-untyped-imports` (or `follow_untyped_imports = true`) | Run |
| The generated `app()` type-checks. | `Argument 1 to "__call__" of "_cached_wrapper" has incompatible type "str | None"; expected "type[Equipment]"  [arg-type]` (`cachetools.cached` under `@classmethod`). | Narrow `# type: ignore[arg-type]` with a comment. | Run |
| Generated entry points type-check. | `app = app()` rebinding: `Incompatible types in assignment` and `has no attribute` errors in `main.py`, `web.py`, `scheduler.py`. | Use `application = app()` when editing them. | Run |
| Container calls are untyped. | With the flags above, `app().inspiring()` is `Inspire`, `app().database().session()` is `Session`; config values are `Any`. | Cast config values; inject with `.as_int()`. | Run |
| Generated code is fully annotated. | `tests/app/test_Inspire.py` and `_inspire` in `app/Scheduler.py` lack return annotations and fail `--disallow-untyped-defs`. | Add `-> None` when touching them; run strict checks only on files you wrote. | Run |

## Database

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `alembic upgrade head` works on a new project. | Fails with the generated `.env`: `ModuleNotFoundError: No module named 'mysql'`. | Set `DB_CONNECTION=sqlite` and `DB_DATABASE=database/database.sqlite`. | Run |
| Switching to SQLite only needs `DB_CONNECTION=sqlite`. | With the leftover `DB_DATABASE=equipment`, SQLite creates `<root>/equipment`. | Also set `DB_DATABASE`. | Run |
| `alembic revision --autogenerate` creates migrations. | Fails: `Can't proceed with --autogenerate option; environment script env.py does not provide a MetaData object`. | `from app.models import Base` and `target_metadata = Base.metadata` in `env.py`. | Run |
| Config comment: MySQL "requires mysqlclient". | The configured `mysql+mysqlconnector` dialect needs `mysql-connector-python`. | Install `mysql-connector-python`. | Source |
| Credentials can contain any character. | The URL is built with an f-string; `p@ss:w/rd` breaks parsing. | Percent-encode the env value. | Run |
| The example `todos` table works on SQLite. | The migration's `BIGINT` primary key is not auto-incremented by SQLite: `NOT NULL constraint failed: todos.id`; `main.py`'s `database_example()` logs `Could not create Todo`. | `BigInteger().with_variant(Integer, "sqlite")` in models and migrations. | Run |
| Unknown `DB_CONNECTION` error is clear. | `ValueError: Unknown queue connection type: <value>` from the database factory. | Read it as a database error. | Run |

## Logging

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| Console channel writes to standard output. | `stream: null` writes to stderr; a string `stream` produces `--- Logging error ---`. | Collect stderr, or add a stdout handler in code. | Run |
| Any `LOG_LEVEL` value is accepted. | Invalid names raise `KeyError` (for example `'VERBOSE'`). | Use standard level names. | Run |
| A missing log directory only affects logging. | `FileNotFoundError` (`single`, `daily`) or `sqlite3.OperationalError` (`sqlite`) at logger creation breaks queue, storage, and database, which all receive the logger. | Create log directories before start. | Run (logger), Source (dependency chain) |
| No warnings during tests. | `DeprecationWarning: pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json` with JSON channels. | Harmless; override the logger in tests. | Run |

## Queue

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `push_at()` runs later with Redis. | The generated worker (`w.work()`) never runs scheduled jobs. | `w.work(with_scheduler=True)` | Run |
| `REDIS_USERNAME` and `REDIS_PASSWORD` configure auth. | Ignored by `RedisQueue` and `queues.py`; `push()` returns `False` with `AuthenticationError`. | Authenticated factory plus worker change in `references/queue.md`. | Run |
| Sync mode surfaces task errors. | Exceptions are logged and swallowed; `push()` returns `False`. | Check the return value. | Run |
| Bad callables fail at `push()` in Redis mode. | Only `__main__` functions make `push()` return `False`. Lambdas, closures, and nested functions from importable modules enqueue (`True`) and then fail in the worker. | Module-level tasks under `app/`; watch RQ's failed job registry. | Run |
| Job modules can `from app import app` at the top (docs' scheduled-task workflow). | If `app/Scheduler.py` imports the job module, importing `app` fails: `ImportError: cannot import name 'app' from 'app'` (circular import). | Import `app` inside the task function. | Run |
| `push_at()` with naive datetimes. | RQ treats naive datetimes as local time. | Safe to use `datetime.now()`. | Run |
| Workers run on Windows. | RQ's default `Worker` uses `os.fork()`; `SimpleWorker` and `SpawnWorker` exist for no-fork platforms. | Switch worker class or use WSL. | Source (not run on Windows) |

## Scheduler

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `self.config.app.env()` works in the scheduler. | The generated scheduler has no `config`; `AttributeError`. | Inject `Equipment.config.app.env` through the constructor. | Run |
| A failing job is logged and skipped. | The exception propagates out of `run()` and stops the process. | Catch exceptions in jobs, or queue the work. | Run |
| `run()` can be called again. | Each call registers every job again. | Call it once; build fresh instances in tests. | Run |
| `schedule.every()` registers jobs. | Equipment runs its own `self.schedule` instance; module-level jobs never run. | Use `self.schedule.every()`. | Source |

## Storage

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `move("a.txt", "archive/a.txt")` works. | Local driver returns `False` when `archive/` does not exist; S3 works. | Write then remove. | Run |
| `list()` returns direct files. | Local: direct files; S3: recursive relative keys such as `sub/b.txt`. | Do not rely on recursion. | Run |
| S3 `list("")` lists the bucket root. | Without `S3_PREFIX`, the first `/` of every key is removed: `['a.txt', 'subb.txt', 'subdeep/c.txt']`. | List named directories, or set a prefix. | Run |
| `list()` of a missing directory. | Local raises `NotADirectoryError`; S3 returns `[]`. | Catch and treat as empty. | Run |
| Writes are text only. | Local `write(bytes)` returns `False`; S3 accepts bytes. | Encode binary data (base64). | Run |
| Paths stay under the storage root. | Local `../x` and absolute paths escape the root. | Generate paths; sanitize labels. | Run |
| S3 `exists()` reports missing objects. | Returns `False` for any error, including auth and network errors. | Check logs when `exists()` is unexpectedly `False`. | Source |

## CLI And Compilation

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| Failures return a non-zero exit code. | Exit code 0 on download failure, declined overwrite, and aborted prompt. | Check for `NAME/pyproject.toml`. | Run |
| Overwriting asks for confirmation. | Answering `y` replaces template files and `.env`, keeps extra files. | Never generate into an existing project. | Run |
| `equipment new` only writes the target directory. | It also writes a template cache into the installed package directory. | Needs a writable install. | Source |
| `compile` packages the app. | It compiles every non-ignored directory, including an in-project `.venv` (6,702 files, 120 MB) and `build/`; it copies `.env`, `storage/`, and `database/` as-is. | Keep venvs outside, clean `dist`/`build`, review copies. | Run |

## Installation

| Docs or expectation | Actual behavior | Fix | Evidence |
|---|---|---|---|
| `pip install .` installs the project. | Also installs top-level packages `app`, `config`, `database`, `storage`, `tests` into `site-packages`; imports from other directories get a stale copy, and projects in one venv collide. | One venv per project; `pip install -e .` during development. | Run |

## Equipment 1.4.0 MCP Template

These are source-checked against the `1.4.0` release tag and current hosted documentation on 2026-11-12. They were not locally run against an MCP client or an HTTP deployment.

| Behavior | Guidance | Evidence |
|---|---|---|
| MCP support is generated-project code, not an Equipment package service. | Use `mcpserver.py`, `config/mcp.yaml`, and FastMCP; remove them and `fastmcp` if unused. | Source (tag `1.4.0`), docs |
| The template declares `fastmcp>=4.1.7,<5`. | Pin the exact FastMCP version tested for production; it may ship breaking minor releases. | Source (tag `1.4.0`), docs |
| Default transport is `stdio`; HTTP uses `config/mcp.yaml` and defaults to `127.0.0.1:8001/mcp`. | Start local MCP servers from the project root and use the project's installed interpreter. | Source (tag `1.4.0`), docs |
| `stdio` uses stdout for protocol messages. | Do not print or otherwise write diagnostics to stdout; use Equipment logging or stderr. | Docs |
| The generated server uses `mask_error_details=True`. | Raise FastMCP `ToolError` only when a safe explanation should be visible to the model; ordinary exception details are masked from clients. | Source (tag `1.4.0`), docs |
| HTTP transport has no authentication by default. | Keep remote access private or behind a gateway, or configure FastMCP authentication. The generated `host_origin_protection='auto'` only validates requests that reach the server through loopback. | Source (tag `1.4.0`), docs |
| A project root module named `mcp.py` shadows the MCP SDK. | Keep the entry point named `mcpserver.py`; rename conflicting modules or directories. | Docs |
| Generated MCP tests use FastMCP's in-memory client. | Test tools without a subprocess or network; restore provider overrides because tests share the cached app container. | Source (tag `1.4.0`), docs |

## Best Practices

- Check this list before copying a docs example into a project.
- Prefer the "Fix" column over the docs example when they conflict, and tell the user why.
- Re-verify an item after upgrading Equipment, `dependency-injector`, `rq`, or `coverage`, because the behavior may have changed.
- Report confirmed gaps upstream at https://github.com/rogervila/equipment/issues when the user wants them fixed at the source.
