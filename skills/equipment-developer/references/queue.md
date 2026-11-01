---
name: "Queues And Workers"
description: "How Equipment's sync and Redis (RQ) queue drivers behave, how to design queued tasks, run workers, schedule delayed jobs, and authenticate Redis."
tags: [equipment, queue, QueueFactory, SyncQueue, RedisQueue, AbstractQueue, push, push_at, redis, rq, worker, queues.py, with_scheduler, enqueue_at, idempotency, REDIS_PASSWORD]
---

# Queues And Workers

`application.queue()` returns a `QueueFactory` that wraps one driver selected by `QUEUE_CONNECTION`: `sync` or `redis`.

## API

| Method | Returns | Behavior |
|---|---|---|
| `push(method, *args, **kwargs)` | `bool` | Run or enqueue `method(*args, **kwargs)`. |
| `push_at(date, method, *args, **kwargs)` | `bool` | Run or enqueue at a `datetime`. |

Any other `QUEUE_CONNECTION` raises `ValueError: Unknown queue connection type: <value>`.

## Configuration

```yaml
queue:
  connection: ${QUEUE_CONNECTION:sync}   # "sync" or "redis"
  connections:
    sync:
    redis:
      host: ${REDIS_HOST:127.0.0.1}
      port: ${REDIS_PORT:6379}
      db: ${REDIS_DB:0}
      username: ${REDIS_USERNAME:null}
      password: ${REDIS_PASSWORD:null}
```

## Driver Behavior

| Behavior | `sync` | `redis` |
|---|---|---|
| Where the work runs | Inline, before `push()` returns. | In a worker process (`python queues.py`). |
| `push()` returns `False` when | The function raised (the exception is logged with `exc_info` and swallowed). | Enqueueing failed (for example connection, auth, or serialization errors). |
| Task exceptions | Swallowed and logged; check the return value. | Recorded by RQ in the worker; check worker logs and the failed job registry. |
| `push_at(date, ...)` | Ignores `date` and runs immediately. | `enqueue_at`; needs a worker started with the RQ scheduler. |
| Functions defined in a `__main__` script | Run normally. | `push()` returns `False` (verified): RQ refuses `__main__` functions at enqueue time. |
| Lambdas, closures, nested functions defined in importable modules | Run normally. | `push()` returns `True`, then the job fails in the worker, which cannot import them (verified). Only RQ's failed job registry shows it. |
| Credentials | Not applicable. | `REDIS_USERNAME` and `REDIS_PASSWORD` are loaded but ignored (verified). |

Because `sync` swallows exceptions, code that "works locally" may be hiding failures. Check the boolean result when it matters:

```python
if not application.queue().push(rebuild_report, report_id):
    raise RuntimeError(f"Could not run rebuild_report for {report_id}")
```

## Designing Tasks

RQ workers import the task by module path and unpickle its arguments. Write tasks like this:

```python
# app/jobs/reports.py
def rebuild_report(report_id: int) -> None:
    from app import app  # imported here: app/__init__.py may import this module

    application = app()
    application.log().info("Rebuilding report", extra={"report_id": report_id})
    application.reports().rebuild(report_id)
```

```python
from app import app
from app.jobs.reports import rebuild_report

app().queue().push(rebuild_report, 123)
```

Rules:

- Import `app` inside the task function. A top-level `from app import app` in a job module that `app/Scheduler.py` imports fails with a circular `ImportError` (verified).
- Annotate every parameter and the `-> None` return; arguments are simple types such as `int` and `str`.
- Module-level functions in an importable module under `app/`. Not lambdas, closures, nested functions, or functions defined in `main.py` when it runs as a script.
- Small, serializable arguments: IDs, short strings, numbers. Load fresh data inside the task.
- Never pass open files, database sessions, request objects, container instances, providers, or large objects.
- Make tasks idempotent. Retries, crashes, and redeploys can run a task more than once. Check whether work was already done, use unique constraints, write deterministic paths, and use idempotency keys with external APIs.
- Log start and finish with stable IDs.

> The generated examples break some of these rules for brevity: `main.py` queues the bound method `app.log().debug`, and `app/Scheduler.py` queues `_inspire` with the logger and service objects as arguments. They work for a demo. Do not copy that pattern into real tasks.

## Running A Redis Worker

```bash
# Redis must be reachable; same .env and working directory as the producers
export QUEUE_CONNECTION=redis    # PowerShell: $env:QUEUE_CONNECTION = "redis"
python queues.py
```

The generated `queues.py`:

```python
# Quoted from the generated queues.py (excerpt, Equipment template, main branch)
config = app.config.queue.connections.redis()

redis = Redis(
    host=config['host'],
    port=int(config['port']),
    db=int(config['db']),
)

w = Worker(['default'], connection=redis)
w.work()
```

It listens on RQ's `default` queue, which is the queue `RedisQueue` uses. Run it from the project root so `app` and your task modules import correctly.

### Delayed Jobs Need The RQ Scheduler

Verified: jobs created with `push_at()` stay in RQ's scheduled registry forever with the generated worker, because `w.work()` does not start the RQ scheduler. Start it in the worker:

```python
w.work(with_scheduler=True)
```

RQ treats naive datetimes as local time (verified with `TZ=Asia/Tokyo`), so `datetime.now() + timedelta(minutes=10)` behaves as expected. Timezone-aware datetimes also work.

### Windows

RQ's default `Worker` runs each job in a child created with `os.fork()` (rq 2.12 source), which native Windows does not provide. RQ also ships `SimpleWorker` (runs jobs in the worker process) and `SpawnWorker` (uses `os.spawn`), both importable from `rq`. On native Windows, switch the worker class or run workers under WSL or Linux. This was not tested on Windows; check the RQ docs for your version.

## Authenticating Redis

`RedisQueue` and the generated `queues.py` build `Redis(host, port, db)` only. Verified against a password-protected Redis: `push()` returns `False` and logs `redis.exceptions.AuthenticationError`, even with `REDIS_PASSWORD` set.

Verified workaround: override the `queue` provider with a factory that swaps in an authenticated RQ queue, and pass the credentials in `queues.py`.

```python
# app/queue_factory.py
from typing import Any

from equipment.Log.AbstractLogger import AbstractLogger
from equipment.Queue.QueueFactory import QueueFactory


def _credential(value: object) -> str | None:
    """YAML turns `null` and empty values into None and may type numeric secrets."""
    return None if value in (None, '', 'null', 'None') else str(value)


class AppQueueFactory(QueueFactory):
    """Equipment's QueueFactory, but Redis connections also send REDIS_USERNAME / REDIS_PASSWORD."""

    def __init__(self, config: dict[str, Any], log: AbstractLogger) -> None:
        if config['connection'] == 'redis':
            from redis import Redis
            from rq import Queue
            from equipment.Queue.RedisQueue import RedisQueue

            redis_config = config['connections']['redis']
            queue = RedisQueue(redis_config, log)
            # RedisQueue ignores credentials; swap in an authenticated RQ queue.
            # `_queue` is a private attribute: re-check this after Equipment upgrades.
            queue._queue = Queue(connection=Redis(
                host=redis_config['host'],
                port=int(redis_config['port']),
                db=int(redis_config['db']),
                username=_credential(redis_config.get('username')),
                password=_credential(redis_config.get('password')),
            ))
            self.queue = queue

        super().__init__(config, log)
```

```python
# app/__init__.py (excerpt: add to the existing file)
from app.queue_factory import AppQueueFactory


class App(Equipment):
    queue = Singleton(AppQueueFactory, Equipment.config.queue, Equipment.log)

    inspiring = Singleton(Inspire, Equipment.config.inspiring.quotes)

    # Reference the local `queue`, not `Equipment.queue`
    scheduler = Singleton(Scheduler, Equipment.log, queue, inspiring)
```

```python
# queues.py (worker side)
redis = Redis(
    host=config['host'],
    port=int(config['port']),
    db=int(config['db']),
    username=config['username'] or None,
    password=str(config['password']) if config['password'] else None,
)

w = Worker(['default'], connection=redis)
w.work(with_scheduler=True)
```

Every provider that needs the queue must reference the overriding `queue`. A provider that references `Equipment.queue` gets a separate, unauthenticated instance (verified).

## Calling From Web Routes And Schedulers

```python
# app/routes/reports.py (excerpt: full module in references/fastapi.md)
@router.post("/reports/{report_id}/rebuild")
def rebuild(report_id: int) -> dict[str, str]:
    if not application.queue().push(rebuild_report, report_id):
        raise HTTPException(status_code=503, detail="Could not queue the job")
    return {"status": "queued"}
```

```python
self.schedule.every().hour.do(self.queue.push, rebuild_report, 123)
```

With `sync`, both run the work inline and block. Use `redis` plus a worker for real background processing.

## Testing

- Test business logic directly; it does not need a queue.
- Test queue integration with `sync`, which runs the task inline:

```python
calls: list[int] = []

def job(value: int) -> None:
    calls.append(value)

self.enterContext(self.app.config.queue.connection.override("sync"))
self.app.queue.reset()                      # rebuild the queue with the overridden config
self.addCleanup(self.app.queue.reset)       # rebuild again after the override ends
self.assertTrue(self.app.queue().push(job, 42))
self.assertEqual([42], calls)
```

- To assert that code enqueues something, override the provider with a mock. Keep your own reference to the mock: the context manager returns a provider wrapper, not the mock.

```python
from unittest.mock import Mock

queue = Mock()
self.enterContext(self.app.queue.override(queue))
# ... call the code under test (create dependent singletons after the override) ...
queue.push.assert_called_once()
```

- Keep Redis-backed tests opt-in, guarded by an environment variable, and never require Redis for the default test run.

## Deployment Checklist

- Redis is reachable from producers and workers, with the same `REDIS_*` settings.
- `QUEUE_CONNECTION=redis` is set on every producer and worker process.
- Workers run `python queues.py` from the project root, with `with_scheduler=True` if you use `push_at`.
- Task modules are importable by the worker and match the producer's code version.
- Credentials are passed explicitly if Redis requires auth.
- Worker logs include task and domain IDs.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Task runs immediately, request blocks | `QUEUE_CONNECTION=sync`. | Use `redis` and a worker. |
| `push()` returns `False` with Redis | `__main__` function, unpicklable argument, connection or auth error. | Use a module-level task with simple arguments; check Redis access and credentials. |
| `push()` returns `True` but the job lands in the failed registry | Lambda, closure, or nested function: enqueued fine, but the worker cannot import it. | Use a module-level task under `app/`. |
| `push()` returns `False` with sync | The task raised. | Read the logged traceback. |
| `AuthenticationError` in logs | Redis requires auth; stock code ignores credentials. | Apply the authenticated factory and worker changes. |
| Delayed jobs never run | Worker started without the RQ scheduler. | `w.work(with_scheduler=True)`. |
| Works with sync, fails with Redis | Importability or serialization. | Pass IDs; move tasks to `app/` modules. |
| Worker cannot import the task | Worker started outside the project root or with older code. | Start from the project root; redeploy workers with producers. |

## Best Practices

- Keep tasks module-level, small, idempotent, and keyed by IDs.
- Check `push()` results when failure matters, especially with `sync`, which swallows exceptions.
- Use `sync` in tests and local development; use Redis plus a worker in production.
- Start workers with `with_scheduler=True` whenever any code calls `push_at()`.
- Authenticate Redis explicitly; the stock driver ignores `REDIS_USERNAME` and `REDIS_PASSWORD`.
- Deploy workers and producers from the same code version.
- Type tasks (`def task(item_id: int) -> None`) and import `app` inside them to avoid circular imports.
