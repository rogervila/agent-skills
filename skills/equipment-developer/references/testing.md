---
name: "Testing Equipment Projects"
description: "Correct unittest and coverage commands for generated projects, the shared-container isolation problem and its fixes, and test patterns for services, config, storage, queues, schedulers, and routes."
tags: [equipment, testing, unittest, TestCase, discover, coverage, coveragerc, faker, mock, override, enterContext, reset_singletons, NullLogger, isolation, fastapi, TestClient]
---

# Testing Equipment Projects

Equipment projects use the standard library `unittest` runner, not pytest. Do not introduce pytest unless the project has already adopted it.

## Install Test Dependencies

`tests/TestCase.py` imports `faker`, which is only in the `dev` extra:

```bash
python -m pip install -e ".[dev]"
```

## Running Tests

Run from the project root. Verified on Python 3.13.17 and 3.15.1:

| Command | Result on a fresh project |
|---|---|
| `python -m unittest` | Passes (default discovery from the project root). |
| `python -m unittest discover -s tests -t .` | Passes. |
| `python -m unittest tests.app.test_Inspire` | Passes. |
| `python -m unittest tests.app.test_Inspire.TestInspire.test_quote` | Passes. |
| `python -m unittest discover -s tests` | Fails: `ImportError: cannot import name 'app' from 'app' (.../tests/app/__init__.py)` |

Why the documented command fails: without `-t`, `unittest` uses `tests/` as the top-level directory and puts it first on `sys.path`. The template's `tests/app/` package then shadows the real `app` package. The same applies to any test package named like a top-level project package. Use `python -m unittest` or add `-t .`.

## Coverage

Verified on a fresh project with `coverage` 7.17:

```bash
python -m coverage run -m unittest
python -m coverage report --omit="*/tests/*,*.pyx"
```

- A plain `python -m coverage report` exits with code 1: `No source for code: '.../src/dependency_injector/providers.pyx'`. It comes from `dependency-injector`'s compiled extension. `coverage erase` does not fix it. Omit `*.pyx`, or use `report -i` to ignore errors.
- The generated `.coveragerc` has `omit = *tests*`. With coverage 7 file patterns, `*` does not cross `/`, so test files are still measured. Use `*/tests/*`.

A `.coveragerc` that works:

```ini
[run]
omit =
    */tests/*
    *.pyx

[report]
omit =
    */tests/*
    *.pyx
```

## The Generated TestCase

```python
# Quoted from the generated tests/TestCase.py (Equipment template, main branch; comments omitted)
import unittest
from faker import Faker
from app import app
# from equipment.Log.NullLogger import NullLogger


class TestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.fake = Faker()
        self.app = app()
        self.app.config.app.env.from_value('testing')
        # self.app.log.override(NullLogger())
```

## The Shared-Container Problem

`app()` returns one cached container per base path for the whole process. Every test method gets the same container, the same singletons, and the same config. Verified:

- A provider override made in one test (`self.app.storage.override(Mock())`) is still active in the next test.
- A config change made with `from_value()` in one test is still visible in the next test.
- `from_value('testing')` in the generated `setUp` permanently changes `app.env` for the process.
- Services created by earlier tests keep the dependencies and config they captured, so later overrides do not reach them.
- Storage and log singletons write into the project's `storage/app/` and `storage/logs/` during tests.

## Isolation Recipe

Use `unittest.TestCase.enterContext()` (Python 3.11+) with the context managers returned by `override()`. Both provider overrides and config option overrides are undone automatically when the test ends (verified):

```python
self.enterContext(self.app.config.queue.connection.override("sync"))

storage = Mock()
self.enterContext(self.app.storage.override(storage))   # keep your own reference to the mock
```

Hardened base class, verified with the generated tests and with cross-test leak checks:

```python
# tests/TestCase.py
import shutil
import tempfile
import unittest

from faker import Faker

from app import App, app
from equipment.Log.NullLogger import NullLogger


class TestCase(unittest.TestCase):
    fake: Faker
    app: App

    def setUp(self) -> None:
        super().setUp()

        self.fake = Faker()
        self.app = app()

        # app() returns one cached container per base path, so start every
        # test from fresh singletons and undo overrides automatically.
        self.app.reset_singletons()
        self.addCleanup(self.app.reset_singletons)
        self.enterContext(self.app.config.app.env.override('testing'))

        # Keep test output quiet and avoid writing storage/logs/app.log.
        self.enterContext(self.app.log.override(NullLogger()))

        # Point local storage at a throwaway directory for this test.
        storage_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, storage_root, True)
        self.enterContext(self.app.config.storage.disk.override('local'))
        self.enterContext(self.app.config.storage.disks.local.path.override(storage_root))
        self.enterContext(self.app.config.queue.connection.override('sync'))
```

The class-level annotations (`fake: Faker`, `app: App`) give every test typed access to `self.app` and `self.fake`; the bare annotation does not shadow the module-level `app()` function. Adapt it to the project. Keep overrides in `setUp`, before any service is created. Changing the shared base class changes every test, so run the full suite afterwards.

## Test Patterns

### Service Through The Container

```python
from tests.TestCase import TestCase


class ReportsTest(TestCase):
    def test_report_is_written_to_storage(self) -> None:
        path = self.app.reports().write_daily_report("Ready")

        self.assertTrue(self.app.storage().exists(path))
        self.assertEqual("Ready", self.app.storage().read(path))
```

### Service With Fakes

Construct the class directly; no container needed. `create_autospec` mocks only the interface's real methods and signatures:

```python
from unittest.mock import Mock, create_autospec

from equipment.Storage.AbstractStorage import AbstractStorage

from app.Reports import Reports
from tests.TestCase import TestCase


class ReportsUnitTest(TestCase):
    def test_uses_storage(self) -> None:
        storage = create_autospec(AbstractStorage, instance=True)
        storage.write.return_value = True
        reports = Reports(storage, Mock(), "reports/daily.txt")

        reports.write_daily_report("Ready")

        storage.write.assert_called_once_with("reports/daily.txt", "Ready")
```

### Overriding A Dependency Of A Registered Service

Override first, then create the dependent service. If it already exists, reset it:

```python
storage = create_autospec(AbstractStorage, instance=True)
storage.write.return_value = True
self.enterContext(self.app.storage.override(storage))
self.app.reports.reset()
self.addCleanup(self.app.reports.reset)

self.app.reports().write_daily_report("Ready")
storage.write.assert_called_once()
```

### Config Values

```python
self.enterContext(self.app.config.reports.output_path.override("test-report.txt"))
self.app.reports.reset()
self.addCleanup(self.app.reports.reset)
```

### Other Areas

| Area | Pattern | Reference |
|---|---|---|
| Database | In-memory SQLite `SQLAlchemyFactory` plus `Base.metadata.create_all()`. | `references/database.md` |
| Storage | Temporary local root through config override; `moto` for S3. | `references/storage.md` |
| Queue | `sync` driver for integration; `Mock` override to assert enqueueing. | `references/queue.md` |
| Scheduler | Fresh instance, `should_exit = True`, patch `equipment.Scheduler.Scheduler.sleep`. | `references/scheduler.md` |
| Logging | `NullLogger` override; `Mock` logger to assert calls. | `references/logging.md` |
| HTTP | FastAPI `TestClient`. | `references/fastapi.md` |

## Test Philosophy

- Test workflows and observable results: files written, rows stored, jobs queued, responses returned.
- Arrange input and config, call a service or entry point, assert the result, then assert important side effects.
- Mock network calls, Redis, S3, email, and payment providers unless the test is an explicit integration test.
- Keep external-service tests (Redis, real S3, MySQL, PostgreSQL) opt-in and skipped by default.
- Use Faker for variety, not for values that assertions depend on. Call `Faker.seed(1234)` when you need reproducible data.
- Never sleep in tests.

## Cross-Platform Notes

- Use `pathlib.Path` and `tempfile`; never hardcode `/` or `\` separators.
- If a test calls `os.chdir()`, change back before deleting the temporary directory. Windows cannot delete the current working directory.
- Close files and log handlers before deleting temporary directories; open handles block deletion on Windows.

## Known Noise

- `DeprecationWarning: pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json` appears when a JSON log channel is built with `python-json-logger` 4.x. It comes from Equipment and is harmless. The hardened `TestCase` avoids it by overriding the logger.

## Best Practices

- Run `python -m unittest` from the project root; never `discover -s tests` without `-t .`.
- Install `.[dev]` before testing, and use `--omit="*/tests/*,*.pyx"` for coverage reports.
- Treat the container as shared state: use `enterContext(...override(...))`, reset singletons, and never leave `from_value()` changes behind.
- Override providers and config before creating the services that depend on them.
- Keep tests fast, deterministic, offline, and free of sleeps.
- Prefer direct construction with fakes for unit tests and the container for workflow tests.
- Annotate test methods with `-> None`, declare `app: App` on the base class, and use `create_autospec(Interface, instance=True)` for framework mocks.
