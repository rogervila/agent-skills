---
name: "Dependency Injection And The App Container"
description: "How the Equipment container, Equipment.make() caching, the generated App composition root, singleton providers, config injection, and provider overrides work."
tags: [equipment, dependency-injector, DeclarativeContainer, DynamicContainer, ThreadSafeSingleton, Singleton, Factory, Configuration, make, app, composition-root, override, reset, reset_singletons, as_int, required]
---

# Dependency Injection And The App Container

Equipment uses the `dependency-injector` library. The framework defines a base container. Each generated project subclasses it in `app/__init__.py` and registers its own services there. That file is the composition root: the single place where concrete services are assembled.

## The Base Container

From `equipment/__init__.py`:

```python
# Quoted from equipment/__init__.py (excerpt, Equipment 1.3.0)
class Equipment(DeclarativeContainer):
    config = Configuration()

    log = Singleton(LoggerFactory, config.app.name, config.base_path, config.log)
    queue = Singleton(QueueFactory, config.queue, log)
    storage = Singleton(StorageFactory, config.storage, config.base_path, log)
    database = Singleton(SQLAlchemyFactory, config.database, config.base_path, log)

    @classmethod
    @cached({})
    def make(cls, base_path: str | None = None): ...


def equipment(base_path: str | None = None) -> Equipment:
    return Equipment.make(base_path)
```

`Singleton` is `dependency_injector.providers.ThreadSafeSingleton`. Every framework service receives the logger, so a broken `config/log.yaml` breaks storage, queue, and database creation too.

## The Generated App Container

```python
# Quoted from the generated app/__init__.py (Equipment template, main branch)
from dependency_injector.providers import ThreadSafeSingleton as Singleton
from equipment import Equipment
from app.Scheduler import Scheduler
from app.Inspire import Inspire


class App(Equipment):
    inspiring = Singleton(Inspire, Equipment.config.inspiring.quotes)

    scheduler = Singleton(
        Scheduler,
        Equipment.log,
        Equipment.queue,
        inspiring
    )


def app(base_path: str | None = None) -> App:
    return App.make(base_path)
```

mypy reports a false positive on `return App.make(base_path)`. When the project is type-checked, silence only that line with `# type: ignore[arg-type]` and a comment; see `references/typing.md`.

Use it from entry points, jobs, and tests:

```python
from app import app

application = app()
application.log().info("Application started")
quote = application.inspiring().quote()
application.storage().write("quote.txt", quote)
```

Calling a provider (`application.storage()`) returns the service. Accessing it without parentheses (`application.storage`) returns the provider, which is what you override in tests.

## How `make()` Works

`App.make(base_path)`:

1. Uses `os.getcwd()` when `base_path` is `None`.
2. Loads `.env` from the base path with `python-dotenv`. Existing process variables win; `.env` does not override them.
3. Creates a container instance and loads `config/*.ini`, then `config/*.yaml`, then `config/*.json`.
4. Sets `config.base_path`.
5. Caches the instance with `cachetools.cached`, keyed by `(class, base_path)`.

Verified consequences:

| Expression | Result |
|---|---|
| `app() is app()` | `True`: one container per process for the same base path. |
| `app() is app(None)` | `True`. |
| `app() is app(os.getcwd())` | `False`: a different cache key, so a second container with its own singletons. |
| `equipment() is app()` | `False`: the base container and `App` are cached separately. |
| `isinstance(app(), App)` | `False`: instances are `dependency_injector` `DynamicContainer` objects. |

Practical rules:

- Call `app()` the same way everywhere (normally without arguments, from the project root) so the whole process shares one container.
- Configuration and `.env` are read once per container. Changing files or environment variables later in the same process has no effect on an existing container.
- Do not use `isinstance(x, App)` checks. Use the `App` return annotation for readability only.
- Because the container is shared, provider overrides and config changes persist for the rest of the process, including across test methods. See `references/testing.md`.

## Registering A Service

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
# app/__init__.py (excerpt: add to the existing file)
from app.Reports import Reports


class App(Equipment):
    # ... existing providers ...
    reports = Singleton(
        Reports,
        Equipment.storage,
        Equipment.log,
        Equipment.config.reports.output_path,
    )
```

```yaml
# config/reports.yaml
reports:
  output_path: "${REPORTS_OUTPUT_PATH:reports/daily.txt}"
```

Prefer constructor injection. It keeps dependencies visible and lets tests build the class directly with fakes. Annotate injected framework services with their interfaces (`AbstractStorage`, `AbstractLogger`, `AbstractQueue`) or `SQLAlchemyFactory`, and config values with the type the injection guarantees. See `references/typing.md`.

Avoid the service-locator pattern inside business services:

```python
# Avoid: hidden dependency on the global container
class InvoiceService:
    def create_invoice(self, customer_id: int) -> int:
        from app import app
        app().log().info("Creating invoice")
        return 1
```

The exception is a process boundary: module-level queue jobs and scheduler callbacks may call `app()` to get the container in a worker process, then delegate to a registered service.

## Provider Lifecycle

- `ThreadSafeSingleton` creates the service on first call and reuses it.
- A singleton captures its dependencies when it is created. Overriding a dependency later does not change already-created dependents. Verified: after `storage.override(fake)`, an existing `reports()` instance keeps the real storage until `reports.reset()`.
- `application.reports.reset()` drops one cached instance.
- `application.reset_singletons()` drops every cached singleton in the container.
- Keep singletons free of per-request mutable state. Request data belongs in function arguments, local variables, database rows, or objects you create per call.

For per-call objects, `dependency-injector` also offers `providers.Factory`:

```python
from dependency_injector.providers import Factory


class App(Equipment):
    invoice_builder = Factory(InvoiceBuilder, Equipment.config.billing.currency)
```

## Injecting Configuration

Config options are providers too. They are evaluated when the dependent service is created.

| Pattern | Result |
|---|---|
| `Equipment.config.reports.output_path` | Raw value (YAML may type it; see `references/configuration.md`). |
| `Equipment.config.web.port.as_int()` | Value converted with `int()`. |
| `Equipment.config.feature.ratio.as_float()` | Value converted with `float()`. |
| `Equipment.config.billing.currency.as_(str.upper)` | Value passed through any callable. |
| `Equipment.config.billing.api_key.required()` | Raises `Undefined configuration option "config.billing.api_key"` when missing, instead of injecting `None`. |

```python
class App(Equipment):
    payments = Singleton(
        PaymentsClient,
        Equipment.config.payments.base_url.required(),
        Equipment.config.payments.timeout.as_int(),
        Equipment.log,
    )
```

## Overriding A Framework Provider

You can replace `log`, `queue`, `storage`, or `database` in `App`, for example to authenticate Redis (see `references/queue.md`). Reference the overriding provider by its local name in the same class body.

```python
class App(Equipment):
    queue = Singleton(AppQueueFactory, Equipment.config.queue, Equipment.log)

    inspiring = Singleton(Inspire, Equipment.config.inspiring.quotes)

    # Use `queue`, not `Equipment.queue`
    scheduler = Singleton(Scheduler, Equipment.log, queue, inspiring)
```

Verified: a provider that still references `Equipment.queue` gets a separate instance built from the base provider, not your override.

## Workers And Schedulers

Queue workers and schedulers run in separate processes. Keep queued callables at module scope, let them create the container with `app()`, and delegate to services:

```python
# app/jobs/invoices.py
def send_invoice(invoice_id: int) -> None:
    from app import app  # imported here: app/__init__.py may import this module

    app().invoices().send(invoice_id)
```

Import `app` inside the function. Verified: when `app/Scheduler.py` (imported by `app/__init__.py`) imports a job module that does a top-level `from app import app`, the import fails with `ImportError: cannot import name 'app' from 'app'` (a circular import), because `app()` is not defined yet while `app/__init__.py` is still running.

## Naming Conventions

- Lowercase provider names: `reports`, `invoices`, `mailer`.
- Class names for services: `Reports`, `InvoiceService`, `Mailer`.
- Keep provider names stable; entry points and tests call them directly.
- Group related providers together in `app/__init__.py` as the app grows.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `AttributeError` when calling `application.reports()` | The provider is not registered on `App`, or the code imported the base `equipment()` container instead of `app()`. |
| A service sees `None` for a config value | The config key is missing or misspelled; missing keys return `None` silently. Use `.required()`. |
| A test or script sees stale config | The singleton was created before the change. Override before first use, or `reset()` the provider. |
| An override has no effect on a dependent service | The dependent singleton already exists, or it references `Equipment.<name>` instead of your overriding provider. |

## Best Practices

- Keep every registration in `app/__init__.py` so the dependency graph is discoverable.
- Inject framework services and config through constructors; call `app()` only at process boundaries.
- Use `.as_int()`, `.as_float()`, and `.required()` instead of casting and validating inside services.
- When overriding a framework provider, update every provider in `App` that should use it.
- Reset or override providers in tests, and undo overrides, because the container is shared for the whole process.
- Keep singleton services stateless with respect to per-request data.
- Type every constructor: framework interfaces for injected services, concrete types for injected config values.
