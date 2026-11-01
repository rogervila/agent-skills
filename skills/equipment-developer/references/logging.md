---
name: "Logging"
description: "How Equipment's LoggerFactory builds standard library loggers from config/log.yaml, how channels and the JSON formatter behave, and how to log safely in apps and tests."
tags: [equipment, logging, LoggerFactory, NullLogger, AbstractLogger, log.yaml, channels, stack, single, daily, console, sqlite, null, json, python-json-logger, extra, stacklevel, LOG_LEVEL, LOG_CHANNEL]
---

# Logging

`application.log()` returns a `LoggerFactory`, a thin wrapper around a standard library `logging.Logger`. Application code calls `debug`, `info`, `warning`, `error`, and `critical`. Where logs go is a configuration decision.

## Configuration

```yaml
log:
  level: ${LOG_LEVEL:debug}
  channel: ${LOG_CHANNEL:stack}

  channels:
    stack:
      channels:
        - single
        - console
    single:
      formatter: json          # "null" or "json"
      filename: 'storage/logs/app.log'
    daily:
      formatter: json
      filename: 'storage/logs/app.log'
      when: 'midnight'
      interval: 1
      backupCount: 7
    console:
      formatter: null
      stream: null
    sqlite:
      filename: 'storage/logs/app.sqlite'
      table_name: logs

  formatters:
    json:
      format: '%(message)s %(asctime)s %(levelname)s %(levelno)d %(pathname)s %(lineno)d'
      indent: null
```

## How The Logger Is Built

From `equipment/Log/LoggerFactory.py`:

- The logger is `logging.getLogger(<app.name>)`, so `APP_NAME` is the logger name. Containers in one process with the same app name share the same `logging.Logger` (verified).
- Creating the factory removes and closes existing handlers on that logger, then adds the handlers for the selected channel.
- The level is `log.level` upper-cased and looked up in `logging.getLevelNamesMapping()`. Valid names: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NOTSET`, plus the aliases `WARN` and `FATAL`. Anything else raises `KeyError` (verified: `LOG_LEVEL=verbose` raises `KeyError: 'VERBOSE'`).
- Each method passes `*args` and `**kwargs` to the standard logger and sets `stacklevel=2` by default, so records show the caller's file and line, not the wrapper (verified).

## Channels

| Channel | Handler | Behavior | Typical use |
|---|---|---|---|
| `stack` | Several | Uses every channel listed in `channels.stack.channels`. | Local development (`single` + `console`). |
| `single` | `FileHandler` | Appends to `<base_path>/<filename>`. | Small deployments, local debugging. |
| `daily` | `TimedRotatingFileHandler` | Rotates by `when`, `interval`, `backupCount`. | One server with short local retention. |
| `console` | `StreamHandler(stream)` | Writes to the stream; `stream: null` means `sys.stderr` (verified). | Containers, PaaS, CI. |
| `sqlite` | `SQLiteLogHandler` (`python_sqlite_log_handler`) | Writes rows to `<base_path>/<filename>`, table `table_name` (default `logs`). | Local inspection, small internal tools. |
| `null` | `NullHandler` | Discards records. `null`, `None`, or an empty value all select it. | Quiet scripts and tests. |

Any other channel name raises `ValueError: Invalid channel name: <name>`.

> The docs describe the console channel as writing to standard output. With the generated `stream: null` it writes to stderr. The `stream` value is passed straight to `StreamHandler`, so a string such as `ext://sys.stdout` does not work: every log call prints `--- Logging error ---` (verified). To log to stdout, override the `log` provider or add a handler in code.

## JSON Formatting

When a channel sets `formatter: json`, Equipment uses `pythonjsonlogger`'s `JsonFormatter` with `formatters.json.format` and `formatters.json.indent`. Fields passed through `extra` appear in the JSON output (verified):

```python
application.log().info("Invoice created", extra={"invoice_id": 7})
```

```json
{"message": "Invoice created", "levelname": "INFO", "lineno": 104, "invoice_id": 7}
```

Add fields such as `name`, `module`, `funcName`, `process`, and `threadName` to `format` when you need them.

With `python-json-logger` 4.x, tests print `DeprecationWarning: pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json` the first time a JSON channel is built. It comes from Equipment's import and is harmless. Do not patch the installed package.

## Usage

```python
from app import app

application = app()
log = application.log()

log.info("Application started")
log.warning("Cache miss", extra={"key": "homepage"})

try:
    risky()
except RuntimeError:
    log.error("Operation failed", exc_info=True)
```

In services, inject the logger instead of calling `app()`:

```python
from equipment.Log.AbstractLogger import AbstractLogger


class Reports:
    def __init__(self, log: AbstractLogger) -> None:
        self.log = log
```

Annotate the dependency as `AbstractLogger`, not `LoggerFactory`, so `NullLogger` and mocks fit the type.

Level guidance:

- `debug`: developer diagnostics.
- `info`: normal lifecycle events.
- `warning`: unexpected but recoverable situations.
- `error`: a failed operation that needs attention.
- `critical`: a severe failure that may need immediate action.

Do not log expected validation failures as `error`.

## File Handlers Need Existing Directories

File-based channels (`single`, `daily`, `sqlite`) open their files when the logger is created. The parent directory must exist. Verified: a missing directory raises `FileNotFoundError` for `single` and `daily`, and `sqlite3.OperationalError: unable to open database file` for `sqlite`, at logger creation. Because `queue`, `storage`, and `database` all receive the logger, a broken log config breaks those services too.

The template ships `storage/logs/` for this reason. If you change a log path, create its directory first, for example at deploy time.

## Choosing A Channel

| Environment | Channel | Why |
|---|---|---|
| Unit tests | `null`, or override with `NullLogger` | No noise and no file locks. |
| Local scripts | `stack` | Console output plus a local file. |
| Docker or PaaS | `console` | The platform collects stderr. |
| One VM | `daily` | Rotating files without extra infrastructure. |
| Local log queries | `sqlite` | Query logs with SQL. Not for high volume. |

## Testing

```python
from equipment.Log.NullLogger import NullLogger

# in a TestCase method or setUp
self.enterContext(self.app.log.override(NullLogger()))
```

`NullLogger` implements the same five methods and discards everything. To assert on logging, inject a `unittest.mock.Mock()` as the logger into the service under test and check its calls.

Tests that read or delete log files must close handlers first, especially on Windows where open handles block deletion.

## Security

Never log secrets, tokens, passwords, private keys, connection URLs with credentials, or personal data. Log stable identifiers (`invoice_id`, `job_id`) in `extra` instead.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No logs at all | `LOG_CHANNEL=null`, a high `LOG_LEVEL`, or the wrong base path. | Check the variables and run from the project root. |
| `KeyError: 'VERBOSE'` (or another name) | Invalid `LOG_LEVEL`. | Use a standard level name. |
| `FileNotFoundError` or `sqlite3.OperationalError: unable to open database file` when any service starts | Log directory missing. | Create the directory or change the path. |
| `--- Logging error ---` on every call | `console.stream` set to a string. | Use `stream: null`, or configure stdout in code. |
| Console output goes to stderr | Expected with `stream: null`. | Configure your collector for stderr, or log to stdout in code. |
| JSON output lacks fields | `formatters.json.format` does not list them. | Add the `LogRecord` attributes you need. |
| Duplicate lines | Custom code added handlers to the same logger name. | Add handlers only through Equipment config, or use a different logger name. |

## Best Practices

- Use `stack` locally and `console` with JSON in production platforms that collect logs.
- Validate `LOG_LEVEL` values and create log directories before the app starts.
- Inject the logger into services; use `extra` for stable identifiers.
- Silence logs in tests with `NullLogger` through a reversible override.
- Keep log volume reasonable in scheduled jobs and queue workers.
- Never log credentials or personal data.
