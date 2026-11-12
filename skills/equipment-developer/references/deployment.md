---
name: "Deployment And Operations"
description: "Process model, per-process environment profiles, driver choices, working-directory requirements, and pre-release checks for running Equipment applications in production."
tags: [equipment, deployment, operations, production, process-model, worker, scheduler, web, mcp, fastmcp, environment, docker, paas, smoke-test, compile, s3, redis, postgresql]
---

# Deployment And Operations

Equipment does not provide a deployment platform, Docker contract, process supervisor, or secret manager. These choices stay with the application. This reference lists what an Equipment app needs from whatever platform you use.

## Process Model

An Equipment app can run up to four kinds of process from the same code:

| Process | Command | Replicas | Notes |
|---|---|---|---|
| Web | `python web.py` or `uvicorn web:web --host ... --port ...` | Any | Stateless if storage, queue, and database are shared services. |
| Worker | `python queues.py` | Any | Needs Redis; add `with_scheduler=True` for `push_at` jobs; see `references/queue.md`. |
| Scheduler | `python scheduler.py` | Exactly one, unless jobs are idempotent or locked | Stops on the first unhandled job exception; supervise and restart it. |
| MCP | Client launches `python mcpserver.py` (`stdio`), or run it as an HTTP service. | As needed | `stdio` is local; HTTP has no authentication by default. See `references/mcp.md`. |
| One-off script | `python main.py` or your own script | As needed | Same config rules as the others. |

Every process calls `app()` and reads config from the working directory. Start every process with the project root as the working directory (for example a container `WORKDIR`), or pass an explicit base path to `app()` in your entry points.

## Choosing Drivers For Production

| Concern | Development | Multi-process production |
|---|---|---|
| Database | `DB_CONNECTION=sqlite` | `postgresql` or `mysql`, with the matching driver installed |
| Queue | `QUEUE_CONNECTION=sync` | `redis` plus worker processes |
| Storage | `FILESYSTEM_DISK=local` | `s3` (or a filesystem shared by every process) |
| Logs | `LOG_CHANNEL=stack` | `console` (stderr) collected by the platform |

## Environment Profiles

```env
# Web process
APP_ENV=production
LOG_CHANNEL=console
LOG_LEVEL=info
DB_CONNECTION=postgresql
QUEUE_CONNECTION=redis
FILESYSTEM_DISK=s3
WEB_HOST=0.0.0.0
PORT=8000
```

```env
# Worker and scheduler processes
APP_ENV=production
LOG_CHANNEL=console
LOG_LEVEL=info
DB_CONNECTION=postgresql
QUEUE_CONNECTION=redis
FILESYSTEM_DISK=s3
```

Plus the connection variables: `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, and the `S3_*` variables.

Operational rules:

- Set real environment variables in the platform. They override `.env`, and `.env` is often absent in production.
- Do not ship the development `.env`. `equipment compile` copies it into the output.
- Percent-encode special characters in `DB_PASSWORD`; see `references/database.md`.
- Pass Redis credentials explicitly; the stock Redis code ignores `REDIS_USERNAME` and `REDIS_PASSWORD`.
- Create log directories before start if you use file channels.
- Keep HTTP MCP behind a private network or gateway, or configure FastMCP authentication. The generated loopback Host/Origin protection does not apply to requests arriving through other interfaces.

## Installing On The Target

```bash
python -m pip install .
```

Install with the same Python minor version you tested. A regular install also copies `app`, `config`, `database`, `storage`, and `tests` into `site-packages`; processes must still start from the project root so the local `config/` and `.env` are used.

Equipment's compile output does not include dependencies. If you ship compiled output, install dependencies on the target separately, build with the target's Python version, and review the copied runtime files. See `references/cli-and-compilation.md`.

## Database Migrations

Run migrations as an explicit release step, from `database/migrations`, with production variables:

```bash
cd database/migrations
alembic upgrade head
```

Review every migration before it reaches production. Avoid running migrations from several replicas at the same time.

## Pre-Release Smoke Test

```bash
python -m pip install -e ".[dev]"
python -m unittest
python main.py
```

If you ship compiled output:

```bash
python -m equipment compile dist
cd dist
python main.pyc
```

Then confirm that Redis, the database, and S3 are reachable from the target environment with the production variables.

## Monitoring

- Monitor worker and scheduler processes like web processes; both are long-running.
- Log task start and finish with stable IDs.
- Watch RQ's failed job registry for task failures.
- Alert when the scheduler process restarts, because a job exception stops it.

## Best Practices

- Run web, worker, and scheduler as separate processes from the same code version.
- Use `stdio` for local MCP clients; deploy HTTP MCP only with authentication and network controls.
- Start every process from the project root.
- Use shared services in production: a server database, Redis, S3, and console logs.
- Keep exactly one scheduler unless jobs are idempotent or locked.
- Inject configuration through real environment variables; never ship a development `.env`.
- Run migrations as a reviewed, single release step.
