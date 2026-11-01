---
name: "Maintaining The Equipment Repository"
description: "Rules, layout, lazy-import constraints, test patterns, validation commands, and change checklists for contributors working on the Equipment framework, its project template, or its docs website."
tags: [equipment, maintenance, contributing, framework, project-template, lazy-imports, __lazy_modules__, pep-810, test_ImportPerformance, unittest, ci, website, docusaurus, llms.txt, dependency-upgrades, cross-platform]
---

# Maintaining The Equipment Repository

Use this reference when the task changes the Equipment repository itself (`rogervila/equipment`): the `equipment/` package, the `project/` template, the tests, or the `website/` docs. For work inside a generated application, use the other references.

The repository ships its own `CLAUDE.md` with the same rules. Read it first when it is present.

## Repository Layout

```text
equipment/                  # framework package published to PyPI
  __init__.py               # Equipment container, equipment(), cli()
  __main__.py               # python -m equipment
  Command/                  # Click CLI: NewProjectCommand, CompileCommand
  Database/                 # SQLAlchemyFactory
  Log/                      # AbstractLogger, LoggerFactory, NullLogger
  Queue/                    # AbstractQueue, QueueFactory, SyncQueue, RedisQueue
  Scheduler/                # AbstractScheduler, Scheduler
  Storage/                  # AbstractStorage, StorageFactory, LocalStorage, S3Storage
project/                    # generated project template (source of truth for equipment new)
tests/                      # framework tests, run from the repository root
website/                    # Docusaurus site; generates llms.txt and llms-full.txt
pyproject.toml              # version = "CURRENT_VERSION" placeholder; deps from requirements.txt
requirements.txt            # runtime and test dependencies of the package
Makefile                    # prepare / build / test
.github/workflows/          # test.yml (3 OS x 3 Python), publish.yml (tags)
```

`project/equipment/` is a git-ignored copy created by `make prepare`. Never edit it; edit `equipment/`.

## Non-Negotiable Rules

1. The test runner is `unittest`. Never suggest pytest.
2. Preserve Python 3.13, 3.14, and 3.15 support, on Windows, macOS, and Linux.
3. Do not change `requirements.txt` unless a dependency upgrade is explicitly requested, and never mix upgrades with other changes.
4. Keep heavy optional dependencies lazy (see below).
5. Use `pathlib` or `os.path`; no hardcoded `/` or `\` in Python logic.
6. Mock the network in `NewProjectCommand` tests; never download the real template in unit tests.
7. Do not hand-edit `website/build/`; it is generated.
8. Keep README, website docs, and the generated LLM files consistent.

## Lazy Imports

Importing `equipment` must not load `boto3`, `botocore`, `redis`, `rq`, `sqlalchemy`, `python_sqlite_log_handler`, or `pythonjsonlogger`. Importing `equipment.Command` must not load `requests`, `urllib3`, or `charset_normalizer`. `tests/test_ImportPerformance.py` enforces both in a subprocess.

- Import heavy dependencies inside the function or factory branch that needs them, as `QueueFactory` does for `RedisQueue` and `LoggerFactory` does for `SQLiteLogHandler` and `JsonFormatter`.
- Use `TYPE_CHECKING` blocks for type-only imports.
- Light modules needed only on some paths are listed in a module-level `__lazy_modules__` placed before the imports (PEP 810). Python 3.15+ defers them; 3.13 and 3.14 ignore the attribute.

| Module | `__lazy_modules__` |
|---|---|
| `equipment/__init__.py` | `dotenv` |
| `equipment/Log/LoggerFactory.py` | `logging.handlers` |
| `equipment/Command/NewProjectCommand.py` | `zipfile` |
| `equipment/Command/CompileCommand.py` | `py_compile` |
| `equipment/Scheduler/Scheduler.py` | `schedule` |

> On Python 3.15+, a lazy `from module import name` binding resolves at first use, so a `mock.patch` of `module.name` active at that moment is kept permanently. Do not add a module to `__lazy_modules__` when tests patch names imported from it, or when its import side effects must run at load time.

## Code Conventions

- Factories (`LoggerFactory`, `QueueFactory`, `StorageFactory`, `SQLAlchemyFactory`) accept a config dict plus dependencies, guard initialization with `if not hasattr(self, '<field>')`, and implement the same interface as the driver they wrap.
- Abstract classes inherit `abc.ABC` and raise `NotImplementedError` (not `@abstractmethod`).
- `open()` calls pass `encoding='utf-8'`.
- 4-space indentation for Python, 2 spaces for YAML, LF line endings, UTF-8 (`.editorconfig`).
- Pylint disables several checks in `.pylintrc`, including `broad-except` and `import-outside-toplevel`.

## Test Patterns

| Area | Pattern |
|---|---|
| Container | Bare `unittest.TestCase` with a config dict loaded through `from_dict`. |
| S3 | `moto.mock_aws()`; never real S3 calls. |
| Files and logs | Temporary directories; close handlers before cleanup. |
| Scheduler | `should_exit = True` and patched `run_pending`; patch `equipment.Scheduler.Scheduler.sleep` to avoid the real one-second sleep. |
| CLI dispatch | `click.testing.CliRunner`, with the command classes mocked. |
| Template scaffold | Build a ZIP from `project/` in memory and patch `_download_project_template`. |
| Duck typing | `runtype.isa()` in some tests. |
| Directory changes | `os.chdir` back before deleting temporary directories (Windows). |

## Validation Commands

```bash
# Framework tests, from the repository root
python -m pip install -r requirements.txt
python -m pip install coverage runtype faker
python -m coverage run -m unittest discover -s tests
python -m coverage report

# A single module
python -m coverage run -m unittest tests.Log.test_LoggerFactory

# Specific interpreters
python3.15 -m coverage run -m unittest discover -s tests
python3.14 -m coverage run -m unittest discover -s tests
python3.13 -m coverage run -m unittest discover -s tests
```

CI runs `discover -s tests` in the repository root, where no test package shadows `equipment`. The same command fails in generated projects; see `references/testing.md`.

Generated project end to end, mirroring the Ubuntu CI job in `.github/workflows/test.yml`. The CI job first builds and installs the working-tree package; without that step, `pip install .` inside `project/` resolves `equipment>=1.0.0` from PyPI (or a stale `project/equipment/` copy from `make prepare`) and your framework changes are not tested.

```bash
# From the repository root: build and install the working-tree package as 9.9.9
python -m pip install build
sed -ri -e 's!CURRENT_VERSION!9.9.9!g' pyproject.toml   # temporary; revert before committing
python -m build
python -m pip install ./dist/equipment-9.9.9.tar.gz
git checkout -- pyproject.toml

# Then validate the template against it
cd project
rm -rf dist equipment
python -m pip install .
python -m coverage run -m unittest
cp .env.example .env
python -m equipment compile dist
cd dist
python main.pyc
```

On Windows, replace the `sed` step with a manual or PowerShell edit of the `version` line, and use `Remove-Item` and `copy` for the file operations.

Website:

```bash
cd website
npm ci
npm run build
test -f build/llms.txt && test -f build/llms-full.txt
```

## Change Checklists

### Framework Service

1. Edit `equipment/<Service>/`.
2. Update or add tests under `tests/<Service>/`.
3. If the config shape changes, update `project/config/<service>.yaml` and the docs.
4. Run the framework tests, then the generated project workflow if the template is affected.

### Project Template

1. Edit files under `project/`.
2. Update `tests/Command/test_NewProjectCommand.py` and `tests/test_PackageMetadata.py` if behavior or metadata changes.
3. Update website docs and, for architecture or constraint changes, the `docusaurus-plugin-llms` root content in `website/docusaurus.config.js`.
4. Validate install, tests, compile, and `python main.pyc` for the generated project.

### Python Version Support

1. Update classifiers in both `pyproject.toml` files and `requires-python` if needed.
2. Update the GitHub Actions matrix.
3. Run tests on every available interpreter.
4. Update README, website docs, and the LLM root content.
5. Document dependency blockers instead of silently upgrading requirements.

### Dependency Upgrade

1. Run the full suite first and note skipped tests and warnings.
2. Upgrade one dependency group at a time in a dedicated change.
3. Run repository tests, generated project validation, and website validation if website dependencies changed.
4. High-risk packages: `dependency-injector`, `SQLAlchemy`, `boto3`/`botocore`/`moto`, `redis`/`rq`, `python-json-logger`, `python_sqlite_log_handler`, `click`, `schedule`, and Docusaurus.

### Documentation

1. Edit `website/docs/*.md` (and `website/docusaurus.config.js` for LLM root content).
2. Prefer copyable commands, Windows notes when commands differ, and required external services.
3. Keep examples aligned with the actual generated files.
4. Rebuild the website; never edit `website/build/`.

## Upstream Candidates Found During Verification

These gaps were verified on 2026-11-01 and are good candidates for upstream fixes. Details and evidence are in `references/verified-behavior.md`.

- Docs recommend `python -m unittest discover -s tests`, which fails in generated projects because `tests/app/` shadows `app`.
- The template `.coveragerc` (`omit = *tests*`) does not omit tests with coverage 7, and `coverage report` fails on `dependency-injector`'s `providers.pyx`.
- `.env.example` (copied to `.env`) sets `APP_ENV=production`, `DB_CONNECTION=mysql`, and `DB_DATABASE=equipment`, unlike the documented SQLite defaults.
- `database/migrations/env.py` ships `target_metadata = None`, so the documented `--autogenerate` command fails.
- `RedisQueue` and `queues.py` ignore `REDIS_USERNAME` and `REDIS_PASSWORD`, and `queues.py` does not start the RQ scheduler needed by `push_at`.
- The docs' scheduler example uses `self.config`, which the generated scheduler does not have.
- `LocalStorage.move()` fails for destinations in missing directories, unlike the docs example; local and S3 `list()` and bytes handling differ; `S3Storage.list("")` without a prefix strips the first `/` of every key.
- `SQLAlchemyFactory` reports unknown connections as `Unknown queue connection type` and does not escape credentials in URLs.
- The CLI exits with code 0 on failures; `equipment compile` compiles in-project virtual environments and `build/`.
- The framework scheduler test patches `time.sleep`, which does not affect the module's `sleep` binding, so it sleeps one second.
- The package has type hints but no `py.typed`, `Equipment.make()` (under `cachetools.cached`) produces a mypy `arg-type` false positive in generated `app()`, and template entry points rebind `app = app()`.
- The docs' scheduled-task workflow (job module with top-level `from app import app`, imported by `app/Scheduler.py`) raises a circular `ImportError`.
- The template's `todos` migration uses a `BIGINT` primary key, which SQLite does not auto-increment, so `main.py`'s database example fails on SQLite.

## Best Practices

- Read the repository `CLAUDE.md` and the maintenance guide before editing.
- Keep changes small and validated on the framework suite and the generated project workflow.
- Keep heavy imports lazy and run `tests/test_ImportPerformance.py` after touching imports.
- Update docs, README, and LLM root content together when behavior or constraints change.
- Never mix dependency upgrades with other work.
- Think about Windows paths, open handles, and current-directory cleanup in every file-system change.
