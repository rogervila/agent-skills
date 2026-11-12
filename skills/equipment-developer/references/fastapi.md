---
name: "FastAPI Entry Point"
description: "How the generated web.py combines FastAPI and Uvicorn with the Equipment container, and how to add routers, keep routes thin, manage sessions, test routes, and run the server."
tags: [equipment, fastapi, uvicorn, web.py, web.yaml, router, APIRouter, TestClient, routes, WEB_HOST, PORT, http, mcp, fastmcp]
---

# FastAPI Entry Point

Generated projects include `web.py`, a minimal FastAPI app that uses the Equipment container. Equipment is not a web framework: it does not provide routing helpers, authentication, request validation, or an API generator. Use FastAPI directly and keep business logic in container services.

## Dependencies And Configuration

The generated `pyproject.toml` includes:

```toml
dependencies = [
    "fastapi[standard]>=0.100.0,<1",  # Remove if web.py will not be used.
    "uvicorn[standard]>=0.30,<1",     # Remove if web.py will not be used.
]
```

```yaml
# config/web.yaml
web:
  host: ${WEB_HOST:0.0.0.0}
  port: ${PORT:8000}
```

`port` loads as an `int` from YAML; `web.py` still casts with `int()`.

## Generated `web.py`

```python
# Quoted from the generated web.py (excerpt, Equipment template, main branch)
from app import app
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from uvicorn import Server, Config

app = app()
app.log().info(...)  # welcome message with host and port

name = app.config.app.name()
web = FastAPI(title=name)


@web.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return f'''
        <h1>{name}</h1>
        <hr />
        <p>{app.inspiring().quote()}</p>
    '''

if __name__ == '__main__':
    try:
        server = Server(Config(
            app='web:web',
            host=str(app.config.web.host()),
            port=int(app.config.web.port()),
        ))
        server.run()
    except KeyboardInterrupt:
        app.log().info('Exiting webserver...')
        exit()
```

Notes:

- Inside `web.py`, the name `app` is the container, not the factory function.
- The FastAPI instance is `web`, so the ASGI import string is `web:web`.
- Importing `web` creates the container and logs the welcome message.
- The `app = app()` rebinding fails type checking. When you edit `web.py`, rename the container variable (verified with mypy and `TestClient`):

```python
#!/usr/bin/env python

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from uvicorn import Config, Server

from app import app
from app.routes.health import router as health_router

application = app()
name = str(application.config.app.name())
web = FastAPI(title=name)
web.include_router(health_router)


@web.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return f"<h1>{name}</h1><hr /><p>{application.inspiring().quote()}</p>"


if __name__ == "__main__":
    Server(Config(
        app="web:web",
        host=str(application.config.web.host()),
        port=int(application.config.web.port()),
    )).run()
```

## Run

```bash
python web.py
```

Open `http://127.0.0.1:8000`. With `WEB_HOST=0.0.0.0` the server listens on all interfaces; local browsers still use `127.0.0.1` or `localhost`.

Uvicorn's own CLI also works from the project root, which helps with process managers and containers:

```bash
uvicorn web:web --host 0.0.0.0 --port 8000
```

## Add A Router

```python
# app/routes/__init__.py   (empty)
```

```python
# app/routes/health.py
from fastapi import APIRouter

from app import app

router = APIRouter()
application = app()   # the same cached container that web.py uses


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": str(application.config.app.name())}
```

```python
# web.py (excerpt: add to the existing file)
from app.routes.health import router as health_router

web.include_router(health_router)
```

Calling `app()` at module level in router modules is safe: it returns the same cached container as long as every module calls it the same way from the project root.

## Keep Routes Thin

Routes translate HTTP to service calls. Business rules live in services registered on `App`:

```python
# app/routes/reports.py
from fastapi import APIRouter, HTTPException

from app import app
from app.jobs.reports import rebuild_report

router = APIRouter()
application = app()


@router.post("/reports/{report_id}/rebuild")
def rebuild(report_id: int) -> dict[str, str]:
    if not application.queue().push(rebuild_report, report_id):
        raise HTTPException(status_code=503, detail="Could not queue the job")
    return {"status": "queued"}
```

- Use queues for slow work triggered by requests. With `QUEUE_CONNECTION=sync` the request blocks until the job finishes.
- Do not store request data on singleton services.
- Use a FastAPI dependency to open and close a database session per request; see `references/database.md`.
- Keep secrets and deployment hostnames in environment variables, not in route modules.

## Testing Routes

FastAPI's `TestClient` works with the generated app (verified: `GET /` returns 200). It needs `httpx`, which `fastapi[standard]` installs.

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router as health_router
from tests.TestCase import TestCase


class WebTest(TestCase):
    def test_health(self) -> None:
        web = FastAPI()
        web.include_router(health_router)
        client = TestClient(web)

        response = client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual("ok", response.json()["status"])
```

Mounting the router on a fresh `FastAPI()` keeps the test independent of `web.py`. `from web import web` also works (verified: `GET /` returns 200), but importing `web` runs its module-level setup.

Test service behavior directly without HTTP; keep HTTP tests for routing, status codes, and serialization.

## Mount MCP On The Same Server

Equipment 1.4.0 also generates `mcpserver.py` with FastMCP. To serve MCP and FastAPI from one process and port, mount the FastMCP HTTP app in `web.py` and use its lifespan so MCP sessions initialize. Combine lifespans if `web.py` already has one. See `references/mcp.md` and the [official MCP example](https://equipment-python.vercel.app/docs/examples/mcp) for the complete pattern.

## Per-Environment Settings

```env
# Local
APP_ENV=local
WEB_HOST=127.0.0.1
PORT=8000
LOG_CHANNEL=stack
QUEUE_CONNECTION=sync
```

```env
# Container or PaaS
APP_ENV=production
WEB_HOST=0.0.0.0
PORT=8000
LOG_CHANNEL=console
QUEUE_CONNECTION=redis
```

## Deployment Notes

- `web.py` runs Uvicorn directly for convenience. Production can use a process manager, a container command, or `uvicorn web:web` with the platform's options.
- Start the process with the project root as the working directory, because `app()` reads config from there.
- Use `LOG_CHANNEL=console` where the platform collects output (the console channel writes to stderr).
- Run a separate Redis worker for queued work.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Route cannot import `app` | Started outside the project root, or the project is not installed. | Start from the root; `python -m pip install -e .`. |
| `TypeError: 'NoneType' object is not subscriptable` on startup | No config found (wrong working directory). | Start from the project root. |
| Port already in use | Another process uses `PORT`. | Change `PORT` or stop the other process. |
| Queued route blocks | `QUEUE_CONNECTION=sync`. | Use Redis and a worker. |
| `TestClient` import fails | `httpx` missing. | Install `fastapi[standard]` or `httpx`. |

## Best Practices

- Keep `web.py` small: create `web`, include routers, and start the server.
- Put routes in `app/routes/` and business logic in registered services.
- Queue slow work and return quickly.
- Manage database sessions per request with dependencies.
- Test HTTP behavior with `TestClient` and service behavior directly.
- Keep host, port, and secrets in configuration and environment variables.
- Protect mounted MCP endpoints with authentication and network controls; the HTTP MCP server is unauthenticated by default.
- Type handlers and dependencies (`Annotated[Session, Depends(...)]`), and use `application = app()` instead of rebinding `app`.
