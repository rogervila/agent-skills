---
name: "Scheduler"
description: "How Equipment's schedule-based Scheduler loop works, how to register jobs, inject configuration, keep jobs safe, and test schedulers without sleeping."
tags: [equipment, scheduler, schedule, Scheduler, AbstractScheduler, scheduler.py, run_pending, should_exit, recurring-jobs, cron, every, at, timezone, testing]
---

# Scheduler

Equipment runs recurring jobs with the `schedule` library. `scheduler.py` creates the app and calls `app.scheduler().run()`, a blocking loop. Run it as its own long-lived process, separate from `main.py`, `web.py`, and `queues.py`.

## Base Class

From `equipment/Scheduler/Scheduler.py`:

```python
# Quoted from equipment/Scheduler/Scheduler.py (Equipment 1.3.0, comments added)
class Scheduler(AbstractScheduler):
    def __init__(self, log: 'AbstractLogger'):
        self.log = log
        self.should_exit = False
        self.schedule = schedule.Scheduler()   # a private scheduler instance

    def run(self) -> None:
        self.log.info('Starting scheduler...')
        while True:
            try:
                self.schedule.run_pending()
                sleep(1)                        # `from time import sleep`
                if self.should_exit:
                    break
            except KeyboardInterrupt:
                self.log.info('Stopping scheduler...')
                _exit()                         # sys.exit
```

Key facts:

- The base class only sets `log`, `schedule`, and `should_exit`. It has no `config` and no `queue`.
- `self.schedule` is a private `schedule.Scheduler()`. Register jobs with `self.schedule.every(...)`. Jobs registered with the module-level `schedule.every(...)` go to the library's default scheduler, which Equipment never runs.
- The loop only catches `KeyboardInterrupt`. Verified: an exception raised by a job propagates out of `run()` and stops the scheduler process. The `schedule` library does not catch job exceptions.
- `should_exit` is checked after each one-second sleep.

## Generated Subclass

```python
# Quoted from the generated app/Scheduler.py (Equipment template, main branch; docstring and comments omitted)
from typing import TYPE_CHECKING
from equipment.Scheduler.Scheduler import Scheduler as Equipment

if TYPE_CHECKING:
    from equipment.Log.AbstractLogger import AbstractLogger
    from equipment.Queue.AbstractQueue import AbstractQueue
    from app.Inspire import Inspire

def _inspire(log: 'AbstractLogger', inspiring: 'Inspire'):
    log.info(inspiring.quote())

class Scheduler(Equipment):
    def __init__(self, log: 'AbstractLogger', queue: 'AbstractQueue', inspiring: 'Inspire'):
        super().__init__(log)
        self.queue = queue
        self.inspiring = inspiring

    def run(self) -> None:
        self.schedule.every(1).seconds.do(
            lambda: self.log.debug(self.inspiring.quote())
        )
        self.schedule.every(5).seconds.do(
            self.queue.push, _inspire, self.log, self.inspiring
        )
        super().run()
```

Registered in `app/__init__.py` as `Singleton(Scheduler, Equipment.log, Equipment.queue, inspiring)`. Note that the module imports the framework class under the alias `Equipment`, which is not the container.

Register jobs first, then call `super().run()` last. The generated `_inspire` has no return annotation; add `-> None` when you touch it, so the file passes the strict type check in `references/typing.md`.

## Registering Jobs

```python
# app/Scheduler.py
from equipment.Log.AbstractLogger import AbstractLogger
from equipment.Queue.AbstractQueue import AbstractQueue
from equipment.Scheduler.Scheduler import Scheduler as Equipment

from app.jobs.cleanup import cleanup_tmp
from app.jobs.reports import rebuild_report


class Scheduler(Equipment):
    def __init__(self, log: AbstractLogger, queue: AbstractQueue) -> None:
        super().__init__(log)
        self.queue = queue

    def run(self) -> None:
        self.schedule.every(10).minutes.do(cleanup_tmp)
        self.schedule.every().day.at("03:00").do(self.queue.push, rebuild_report, 123)
        self.schedule.every().monday.do(cleanup_tmp)
        self.schedule.every(5).to(10).minutes.do(cleanup_tmp)
        super().run()
```

When you change the constructor, update the `scheduler` registration in `app/__init__.py` to pass the same arguments.

`app/__init__.py` imports `app/Scheduler.py`, which imports the job modules. Job modules must therefore import `app` inside their functions, not at module level, or the import fails with a circular `ImportError` (verified; see `references/queue.md`).

- Short work can run inline. Push slow work to the queue so the loop stays responsive.
- With `QUEUE_CONNECTION=sync`, `self.queue.push` still runs the work inline.
- `.at("03:00")` uses the process's local time. `schedule` 1.2.2 also accepts a timezone, `.at("03:00", "Europe/Madrid")`, which imports `pytz`; add `pytz` to the project dependencies before using it.
- Choose intervals longer than the work takes.

## Injecting Configuration

The docs show `self.config.app.env()` inside a scheduler. The generated scheduler has no `config` attribute, so that example raises `AttributeError` as written (verified: generated scheduler attributes are `inspiring`, `log`, `queue`, `schedule`, `should_exit`). Inject the values you need instead (verified pattern):

```python
# app/Scheduler.py
from equipment.Log.AbstractLogger import AbstractLogger
from equipment.Queue.AbstractQueue import AbstractQueue
from equipment.Scheduler.Scheduler import Scheduler as Equipment

from app.Inspire import Inspire
from app.jobs.reports import rebuild_report


class Scheduler(Equipment):
    def __init__(self, log: AbstractLogger, queue: AbstractQueue, inspiring: Inspire, env: str) -> None:
        super().__init__(log)
        self.queue = queue
        self.inspiring = inspiring
        self.env = env

    def run(self) -> None:
        if self.env == "production":
            self.schedule.every().day.at("03:00").do(self.queue.push, rebuild_report, 123)
        else:
            self.log.info("Skipping production-only jobs")
        super().run()
```

```python
# app/__init__.py (excerpt: add to the existing file)
class App(Equipment):
    inspiring = Singleton(Inspire, Equipment.config.inspiring.quotes)
    scheduler = Singleton(
        Scheduler,
        Equipment.log,
        Equipment.queue,
        inspiring,
        Equipment.config.app.env,
    )
```

When scheduling settings grow, add `config/scheduler.yaml` and inject those values the same way.

## Writing Safe Jobs

Good scheduled jobs are short, idempotent, logged, exception-safe, independent of terminal state, and safe to run again after a restart. Because one exception stops the loop, wrap job bodies:

```python
# app/safe_job.py
import functools
from collections.abc import Callable

from equipment.Log.AbstractLogger import AbstractLogger


def safe_job[**P](log: AbstractLogger) -> Callable[[Callable[P, object]], Callable[P, None]]:
    """Log job exceptions instead of letting them stop the scheduler loop."""

    def decorator(func: Callable[P, object]) -> Callable[P, None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            try:
                func(*args, **kwargs)
            except Exception:
                log.error("Scheduled job failed", extra={"job": getattr(func, "__name__", repr(func))}, exc_info=True)

        return wrapper

    return decorator
```

Use it when registering: `self.schedule.every(10).minutes.do(safe_job(self.log)(cleanup_tmp))`. The PEP 695 `[**P]` syntax needs Python 3.12+, which every Equipment project has.

Or push the work to the queue, where failures stay inside the worker.

## Process Model

- Run exactly one scheduler process when a job must happen once globally. Every replica runs every job.
- If you need several replicas, make jobs idempotent or protect them with an external lock.
- Supervise the scheduler like any other worker; it stops on the first unhandled job exception.
- Document timezone assumptions for `.at()` jobs.

## Testing

Test task functions directly. Test registration separately, without sleeping. Verified details:

- Patching `time.sleep` does not help: the module bound `sleep` at import (`from time import sleep`), and a run with that patch still took 1.00 s. Patch `equipment.Scheduler.Scheduler.sleep` instead (0.00 s).
- Set `should_exit = True` before `run()` so the loop ends after one iteration.
- Calling `run()` twice on the same instance registers every job twice. The container's `scheduler()` is a singleton, so build a fresh instance in tests.

```python
from unittest import mock

from equipment.Log.NullLogger import NullLogger
from app.Scheduler import Scheduler
from tests.TestCase import TestCase


class SchedulerTest(TestCase):
    def test_registers_jobs_without_sleeping(self) -> None:
        scheduler = Scheduler(NullLogger(), mock.Mock(), mock.Mock())
        scheduler.should_exit = True

        with mock.patch("equipment.Scheduler.Scheduler.sleep"), \
                mock.patch.object(scheduler.schedule, "run_pending"):
            scheduler.run()

        self.assertEqual(2, len(scheduler.schedule.get_jobs()))
```

This test targets the generated three-argument constructor. Pass the extra arguments if your scheduler takes more, for example `"production"` for the `env` version above.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A job never runs | `scheduler.py` not running, job registered after `super().run()`, registered on module-level `schedule`, or clock/timezone mismatch. | Register on `self.schedule` before `super().run()`; check the clock. |
| Scheduler process exits unexpectedly | A job raised an exception. | Catch exceptions inside jobs, or queue the work. |
| The loop blocks | A job does long work inline. | Push it to the queue. |
| Jobs run several times | Several scheduler processes, or `run()` called more than once. | Run one scheduler; call `run()` once. |
| `AttributeError: 'Scheduler' object has no attribute 'config'` | Copied the docs' environment example. | Inject the value through the constructor. |
| Scheduler tests take one second each | Patched `time.sleep`. | Patch `equipment.Scheduler.Scheduler.sleep`. |

## Best Practices

- Register jobs on `self.schedule`, then call `super().run()` last.
- Inject config values and services through the constructor; there is no `self.config`.
- Keep jobs short and exception-safe; queue slow work.
- Run a single scheduler replica unless jobs are idempotent or locked.
- Test task functions directly, and test registration with a fresh instance, `should_exit = True`, and a patched module `sleep`.
- Type the scheduler constructor with `AbstractLogger` and `AbstractQueue`, and keep job modules free of top-level `from app import app`.
