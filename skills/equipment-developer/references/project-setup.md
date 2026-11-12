---
name: "Project Setup And Structure"
description: "How to install Equipment, create and configure a generated project, understand its files and entry points, and decide where new code goes."
tags: [equipment, installation, equipment-new, project-structure, entry-points, main.py, web.py, mcpserver.py, fastmcp, queues.py, scheduler.py, virtualenv, pip, pyproject, env-file, first-run]
---

# Project Setup And Structure

Equipment is a scaffolding framework. `equipment new NAME` creates a normal Python project that you own and edit. The `equipment` package stays installed as a library that provides configuration loading, the dependency injection container, and the log, queue, storage, and database factories.

## Requirements

- Python 3.13, 3.14, or 3.15 (`requires-python = ">=3.13"`).
- Windows, macOS, or Linux.
- `pip` for the interpreter you will use.
- Network access to GitHub when running `equipment new`.
- Optional services, depending on configuration: Redis, S3-compatible storage, MySQL, or PostgreSQL.
- Generated projects include an optional FastMCP server; remove it and its dependency if unused.

## Install The CLI

```bash
python -m pip install equipment
# or, as an isolated command-line tool
pipx install equipment
```

Windows can select an interpreter with the launcher:

```bat
py -3.14 -m pip install equipment
```

Other dependency managers work too (`pipenv install equipment`, `poetry add equipment`). Prefer `python -m pip ...` so packages install into the interpreter that runs the code.

## Create A Project

```bash
equipment new my-app
cd my-app
```

Use short lowercase names with hyphens or underscores, such as `billing-api` or `data_worker`. Avoid spaces, shell metacharacters, and path separators. See `references/cli-and-compilation.md` for exactly what the command does, including its overwrite behavior and exit codes.

## First-Run Configuration

`equipment new` copies `.env.example` to `.env`. The template's `.env.example` is a production-flavoured example, not a local profile. Verified values in the generated `.env`:

| Variable | Generated `.env` value | Effect if left unchanged |
|---|---|---|
| `APP_ENV` | `production` | The app reports `production` locally. |
| `DB_CONNECTION` | `mysql` | `app.database()` and Alembic fail with `ModuleNotFoundError: No module named 'mysql'` until `mysql-connector-python` is installed. After that, queries fail until a MySQL server is reachable (the engine connects on first use). |
| `DB_DATABASE` | `equipment` | If you switch only `DB_CONNECTION` to `sqlite`, SQLite creates a file named `equipment` in the project root. |
| `QUEUE_CONNECTION` | `sync` | Jobs run inline. |
| `FILESYSTEM_DISK` | `local` | Files go to `storage/app/`. |
| `LOG_CHANNEL` | `stack` | Logs go to `storage/logs/app.log` and to stderr. |

The YAML defaults (`APP_ENV=local`, `DB_CONNECTION=sqlite`, `DB_DATABASE=database/database.sqlite`) only apply when the variables are not set. For local development, edit `.env`:

```env
APP_NAME=My App
APP_ENV=local
LOG_CHANNEL=stack
LOG_LEVEL=debug
DB_CONNECTION=sqlite
DB_DATABASE=database/database.sqlite
QUEUE_CONNECTION=sync
FILESYSTEM_DISK=local
```

> `.env` is git-ignored by the generated `.gitignore` (`*.env`). Keep real secrets there or in the process environment, never in `config/*.yaml`.

## Install The Project

Docs use a regular install:

```bash
python -m pip install .
python -m pip install ".[dev]"   # adds coverage, faker, pylint, flake8, autopep8, runtype
```

`tests/TestCase.py` imports `faker`, which is only in the `dev` extra. Install `.[dev]` before running tests. Quote `".[dev]"` in shells such as zsh that expand brackets.

Verified install behavior to know about:

- The generated `pyproject.toml` uses `packages.find` with `include = ["*"]`. A regular `pip install .` copies top-level packages named `app`, `config`, `database`, `storage`, and `tests` into `site-packages`.
- That copy is a snapshot. Code that runs from the project root still imports the local `app/` first, but any process whose working directory is elsewhere imports the stale copy.
- Two Equipment projects installed into one environment both provide a package named `app`. Use one virtual environment per project.
- `python -m pip install -e ".[dev]"` (editable install) maps `app` to the project directory and avoids stale copies. Prefer it during development.

Virtual environment location: docs suggest `python -m venv .venv` inside the project. That works for development, but `equipment compile` walks every directory except a short ignore list, so an in-project `.venv` and a setuptools `build/` directory get compiled into the output. Keep the virtual environment outside the project, or compile from a clean copy. See `references/cli-and-compilation.md`.

## Verify The Project

From the project root:

```bash
python main.py
python -m unittest
```

`python main.py` only logs a welcome message. The example functions in `main.py` (`storage_example`, `queue_example`, `database_example`, `log_example`) are defined but not called.

> Use `python -m unittest` (or `python -m unittest discover -s tests -t .`). The docs' `python -m unittest discover -s tests` fails on a fresh project because `tests/app/` shadows the `app` package. See `references/testing.md`.

## Generated Layout

```text
my-app/
├── __init__.py              # empty; the project root is also a package
├── app/
│   ├── __init__.py          # App container (composition root) and app() helper
│   ├── Inspire.py           # example service
│   └── Scheduler.py         # example scheduler subclass
├── config/
│   ├── app.yaml             # app.name, app.env
│   ├── database.yaml        # sqlite, mysql, postgresql connections
│   ├── inspiring.json       # example data for Inspire
│   ├── log.yaml             # level, channel, channels, formatters
│   ├── mcp.yaml             # MCP transport, host, port, path
│   ├── queue.yaml           # sync or redis
│   ├── storage.yaml         # local or s3
│   └── web.yaml             # host and port for web.py
├── database/
│   ├── .gitignore           # ignores *.sqlite*
│   └── migrations/          # Alembic: alembic.ini, env.py, script.py.mako, versions/
├── storage/
│   ├── app/                 # local storage root (content git-ignored)
│   └── logs/                # file log output (content git-ignored)
├── tests/
│   ├── __init__.py
│   ├── TestCase.py          # unittest base class with Faker and the app container
│   ├── test_mcpserver.py
│   └── app/
│       ├── __init__.py
│       └── test_Inspire.py
├── .coveragerc  .editorconfig  .env  .env.example  .gitignore
├── main.py  queues.py  scheduler.py  web.py  mcpserver.py
├── pyproject.toml           # name replaced with your project name
└── README.md
```

## Ownership

| Path | Owner | Purpose |
|---|---|---|
| `app/__init__.py` | You | Service registrations; the composition root. |
| `app/*.py`, `app/<domain>/` | You | Business services, repositories, jobs, routes. |
| `config/*.yaml`, `config/*.json`, `config/*.ini` | You | Settings; each file usually holds one top-level key named after the file. |
| `config/mcp.yaml` | You | Transport, host, port, and path used by `mcpserver.py`. |
| `database/migrations/` | You | Alembic environment and revisions. |
| `storage/app/`, `storage/logs/` | Runtime | Local files and logs; not committed. |
| `tests/` | You | `unittest` tests. |
| `main.py`, `web.py`, `mcpserver.py`, `queues.py`, `scheduler.py` | You | Process entry points. |
| `.env.example` | You | Documented variable template; keep values fake. |
| `.env` | Local runtime | Local overrides and secrets; git-ignored. |
| `equipment` package | Framework | Installed library. Do not edit it in `site-packages`. |

## Entry Points

| File | What it does | Needs |
|---|---|---|
| `main.py` | `app = app()`, logs a welcome message, defines example functions. | Nothing external. |
| `scheduler.py` | `app = app()`, logs, then `app.scheduler().run()` (blocking loop). | Whatever the jobs need. |
| `queues.py` | Builds `Redis(host, port, db)` from `config/queue.yaml` and runs `rq.Worker(['default']).work()`. | Redis. Ignores `REDIS_USERNAME`, `REDIS_PASSWORD`, and scheduled jobs; see `references/queue.md`. |
| `web.py` | Creates `FastAPI(title=app.config.app.name())`, one `/` route, and runs Uvicorn with `config/web.yaml` host and port. | `fastapi[standard]`, `uvicorn[standard]`. |
| `mcpserver.py` | Exposes app services as MCP tools, resources, and prompts through FastMCP. | `fastmcp`; `config/mcp.yaml`. |

Every entry point rebinds the module-level name `app` to the container (`app = app()`). Inside those files, `app` is the container, not the factory function.

## Run From The Project Root

`app()` uses the current working directory as the base path. It loads `.env` and `config/*` from there and resolves relative paths (SQLite file, log files, local storage) against it.

Running from another directory, for example `python /path/to/my-app/main.py`, finds no config. The first service creation then fails. Verified signature:

```text
TypeError: 'NoneType' object is not subscriptable
```

Fix it by running from the project root (`cd my-app`), by setting the working directory in your process manager or container, or by passing an explicit base path: `app("/path/to/my-app")`.

## Where To Put New Code

Small projects can use flat modules:

```text
app/
├── __init__.py
├── Billing.py
├── Reports.py
├── jobs.py
└── Scheduler.py
```

Larger projects can group by domain:

```text
app/
├── __init__.py
├── billing/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── service.py
├── jobs/
│   ├── __init__.py
│   └── reports.py
├── routes/
│   ├── __init__.py
│   └── health.py
└── Scheduler.py
```

Write every new module fully type-annotated and check it with mypy; see `references/typing.md`. Register only services that need container-managed dependencies in `app/__init__.py`. Plain helpers, value objects, and ORM models do not need registrations. The generated code uses PascalCase module names (`Inspire.py`, `Scheduler.py`); follow the convention the project already uses.

## Removing Optional Features

`equipment new` has no feature flags. Start from the full template and remove what you do not need, together with its tests, config, and docs:

| Feature not needed | Remove |
|---|---|
| Web | `web.py`, `config/web.yaml`, and the `fastapi[standard]` and `uvicorn[standard]` dependencies. |
| MCP | `mcpserver.py`, `config/mcp.yaml`, `tests/test_mcpserver.py`, and the `fastmcp` dependency. |
| Redis workers | `queues.py`; keep `config/queue.yaml` with `sync`, because the container builds `queue` from it. |
| Recurring jobs | `scheduler.py`, `app/Scheduler.py`, and the `scheduler` registration in `app/__init__.py`. |
| Relational schema | `database/migrations/` and the `alembic` dependency; keep `config/database.yaml` unless you never call `app.database()`. |
| Example service | `app/Inspire.py`, `config/inspiring.json`, `tests/app/test_Inspire.py`, the `inspiring` registration, and its uses in `app/Scheduler.py` and `web.py`. |

> The base container always defines `log`, `queue`, `storage`, and `database` providers. Providers are only built when called, so unused ones cost nothing, but `config/log.yaml` must stay valid because every other framework service receives the logger.

## Best Practices

- Fix the generated `.env` before first use: `APP_ENV=local`, `DB_CONNECTION=sqlite`, `DB_DATABASE=database/database.sqlite`.
- Use one virtual environment per Equipment project, and prefer `python -m pip install -e ".[dev]"` during development.
- Run every entry point and test command from the project root, or pass an explicit base path to `app()`.
- Run MCP over `stdio` for local clients; protect HTTP transport with a private network, gateway, or FastMCP authentication.
- Keep the virtual environment outside the project if you plan to use `equipment compile`.
- Remove unused optional features completely: code, config, dependencies, tests, and docs together.
- Read the generated files instead of assuming they match docs examples, because `equipment new` always uses the latest template.
