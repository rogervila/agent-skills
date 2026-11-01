---
name: "Database And Migrations"
description: "How Equipment's SQLAlchemyFactory builds connections, how to use engines, sessions, and raw SQL safely, and how to run Alembic migrations in a generated project."
tags: [equipment, database, sqlalchemy, SQLAlchemyFactory, engine, session, text, sqlite, mysql, postgresql, mysql-connector-python, psycopg2, alembic, migrations, target_metadata, autogenerate, repository]
---

# Database And Migrations

Equipment wraps SQLAlchemy setup in `SQLAlchemyFactory`. It builds a URL from `config/database.yaml`, creates an engine and a session factory, and exposes a `text()` helper. Your application owns models, schema, migrations, repositories, and transaction boundaries.

## API

`application.database()` returns the singleton `SQLAlchemyFactory`, created on first call.

| Member | Description |
|---|---|
| `url` | The SQLAlchemy URL string built from config. |
| `engine` | `sqlalchemy.Engine` from `create_engine(url)`. |
| `session()` | A new `sqlalchemy.orm.Session` from `sessionmaker(bind=engine)`. |
| `text(query)` | Static helper returning `sqlalchemy.text(query)`. |

## Configuration And URLs

```yaml
database:
  connection: ${DB_CONNECTION:sqlite}
  connections:
    sqlite:
      schema: sqlite
      database: "${DB_DATABASE:database/database.sqlite}"
    mysql:
      schema: "mysql+mysqlconnector"
      host: ${DB_HOST:127.0.0.1}
      port: ${DB_PORT:3306}
      database: ${DB_DATABASE:database}
      username: ${DB_USERNAME:root}
      password: ${DB_PASSWORD:password}
      charset: ${DB_CHARSET:utf8mb4}
    postgresql:
      schema: "postgresql+psycopg2"
      host: ${DB_HOST:127.0.0.1}
      port: ${DB_PORT:5432}
      database: ${DB_DATABASE:database}
      username: ${DB_USERNAME:root}
      password: ${DB_PASSWORD:password}
```

| `DB_CONNECTION` | URL built by Equipment | Driver package |
|---|---|---|
| `sqlite` (file) | `sqlite:///<base_path>/<database>` | Standard library |
| `sqlite` with `database: ":memory:"` | `sqlite://` | Standard library |
| `mysql` | `{schema}://{username}:{password}@{host}:{port}/{database}?charset={charset}` | `mysql-connector-python` for the default `mysql+mysqlconnector` schema |
| `postgresql` | `{schema}://{username}:{password}@{host}:{port}/{database}` | `psycopg2-binary` (or `psycopg2`) for `postgresql+psycopg2` |

Notes:

- The generated `pyproject.toml` lists drivers as comments. Uncomment or add the one you need, then reinstall the project.
- The comment in `config/database.yaml` mentions `mysqlclient`, but the configured `mysql+mysqlconnector` dialect needs `mysql-connector-python`. `mysqlclient` serves the `mysql+mysqldb` dialect.
- Any other `DB_CONNECTION` value raises `ValueError: Unknown queue connection type: <value>`. The message says "queue", but it comes from the database factory.
- Relative SQLite paths resolve against the base path, so the file location depends on where the process starts.

## Generated `.env` Pitfalls

The generated `.env` sets `DB_CONNECTION=mysql`, `DB_DATABASE=equipment`, `DB_USERNAME=equipment`, and `DB_PASSWORD=equipment`. Verified outcomes:

| `.env` state | Outcome |
|---|---|
| Unchanged, no MySQL driver | `ModuleNotFoundError: No module named 'mysql'` on `app.database()` and on `alembic upgrade head`. |
| Only `DB_CONNECTION=sqlite` changed | SQLite creates a database file named `equipment` in the project root. |
| `DB_CONNECTION=sqlite` and `DB_DATABASE=database/database.sqlite` | Works; the file lands in `database/` and is git-ignored. |

## Credentials With Special Characters

Equipment builds the URL with an f-string and does not escape credentials. Verified: the password `p@ss:w/rd` produces a URL that SQLAlchemy cannot parse (`ValueError: invalid literal for int() with base 10: 'w'`).

Percent-encode special characters in the environment value. SQLAlchemy decodes them when it parses the URL (verified):

```bash
python -c "from urllib.parse import quote_plus; print(quote_plus('p@ss:w/rd'))"
# p%40ss%3Aw%2Frd
```

```env
DB_PASSWORD=p%40ss%3Aw%2Frd
```

Also quote the YAML placeholder (`password: "${DB_PASSWORD:password}"`) so numeric-looking passwords stay strings.

## Raw SQL

```python
from app import app

application = app()
database = application.database()

with database.engine.connect() as connection:
    result = connection.execute(
        database.text("SELECT * FROM todos WHERE id = :todo_id"),
        {"todo_id": todo_id},
    )
    todo = result.mappings().first()
```

Always use bind parameters for values. Never format user input into SQL strings.

## ORM Sessions And Transactions

Define one typed declarative `Base` for the application, for example in `app/models.py`. Use SQLAlchemy 2.x `DeclarativeBase` and `Mapped[...]` so models are checked by mypy (see `references/typing.md`):

```python
# app/models.py
from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLite only auto-increments INTEGER primary keys; keep BIGINT elsewhere.
BigId = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    completed: Mapped[bool]
```

`Mapped[str]` is `NOT NULL`; use `Mapped[str | None]` for nullable columns.

### SQLite And `BIGINT` Primary Keys

SQLite only auto-generates values for `INTEGER PRIMARY KEY` columns. The template's example migration creates `todos.id` as `BIGINT`. Verified on SQLite: inserts without an explicit `id` fail with `sqlite3.IntegrityError: NOT NULL constraint failed: todos.id`, and `main.py`'s `database_example()` only logs `Could not create Todo`.

Use the `BigId` variant above in models, and the same variant in migrations before applying them to SQLite:

```python
sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True)
```

MySQL and PostgreSQL keep `BIGINT`.

`session()` returns a standard SQLAlchemy 2.x `Session`, so the context-manager form works and keeps boundaries explicit:

```python
with application.database().session() as session, session.begin():
    session.add(Todo(title="Learn Equipment", completed=False))
# committed here, or rolled back if an exception escaped; the session is closed
```

The docs' explicit form is equivalent:

```python
session = application.database().session()
try:
    session.add(todo)
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

> `main.py` defines its example `Todo` model inside a function with its own `declarative_base()`. Treat it as a demo; real models belong in a module with one shared `Base`.

## Repository Pattern

```python
# app/repositories/TodoRepository.py
from sqlalchemy import select

from equipment.Database.SQLAlchemyFactory import SQLAlchemyFactory

from app.models import Todo


class TodoRepository:
    def __init__(self, database: SQLAlchemyFactory) -> None:
        self.database = database

    def latest(self) -> Todo | None:
        with self.database.session() as session:
            return session.scalars(select(Todo).order_by(Todo.id.desc()).limit(1)).first()

    def add(self, title: str) -> int:
        with self.database.session() as session, session.begin():
            todo = Todo(title=title, completed=False)
            session.add(todo)
            session.flush()
            return todo.id
```

```python
# app/__init__.py (excerpt: add to the existing file)
from app.repositories.TodoRepository import TodoRepository


class App(Equipment):
    todos = Singleton(TodoRepository, Equipment.database)
```

Keep SQLAlchemy calls in repositories so routes, jobs, and scheduler callbacks stay free of database details.

## Alembic Migrations

The template ships an Alembic environment in `database/migrations/`:

| File | Purpose |
|---|---|
| `alembic.ini` | `script_location = .`, so run Alembic from this directory. |
| `env.py` | Builds the app with the project root as base path and sets `sqlalchemy.url` from `app.database().url`. |
| `versions/2fd79d00428b_create_todos_table.py` | Example first migration that creates `todos`. |

Run commands from `database/migrations`:

```bash
cd database/migrations
alembic upgrade head
alembic current
alembic revision -m "add invoices table"          # empty revision you fill in
```

Because `env.py` uses the project root as base path, the project `.env` applies, including its `DB_CONNECTION`.

### Enabling Autogenerate

The generated `env.py` sets `target_metadata = None`. Verified: `alembic revision --autogenerate` then fails with:

```text
FAILED: Can't proceed with --autogenerate option; environment script env.py does not provide a MetaData object or sequence of objects to the context.
```

Point it at your models. Replace the `target_metadata = None` line in `database/migrations/env.py` (after the existing `app = application.app(...)` block):

```python
from app.models import Base

target_metadata = Base.metadata
```

Verified: with that change, `alembic revision --autogenerate -m "create invoices table"` generated the expected `op.create_table(...)` calls.

### Migration Workflow

1. Change or add ORM models.
2. Generate a revision (`--autogenerate`, or write it by hand).
3. Read the generated file. Check indexes, constraints, nullability, defaults, and destructive operations.
4. Apply it locally with `alembic upgrade head`.
5. Run the tests.
6. Apply it in staging and production with your deployment controls.

If you keep the example `todos` table, your models must match it, or autogenerate will propose changes. If you do not want it, delete the example revision before the first real migration.

## Sessions In FastAPI Routes

Use a dependency so every request closes its session:

```python
# app/routes/todos.py
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import app
from app.models import Todo

router = APIRouter()


def get_session() -> Iterator[Session]:
    with app().database().session() as session:
        yield session


@router.get("/todos/latest")
def latest(session: Annotated[Session, Depends(get_session)]) -> dict[str, str | None]:
    todo = session.scalars(select(Todo).order_by(Todo.id.desc()).limit(1)).first()
    return {"title": todo.title if todo is not None else None}
```

Include it in `web.py` with `web.include_router(router)`.

## Testing Database Code

Build a factory on in-memory SQLite and create the schema directly (verified pattern):

```python
from equipment.Database.SQLAlchemyFactory import SQLAlchemyFactory
from equipment.Log.NullLogger import NullLogger

from app.models import Base
from app.repositories.TodoRepository import TodoRepository
from tests.TestCase import TestCase


class TodoRepositoryTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.database = SQLAlchemyFactory(
            {"connection": "sqlite", "connections": {"sqlite": {"schema": "sqlite", "database": ":memory:"}}},
            "",
            NullLogger(),
        )
        Base.metadata.create_all(self.database.engine)
        self.repository = TodoRepository(self.database)

    def test_latest_returns_none_when_empty(self) -> None:
        self.assertIsNone(self.repository.latest())

    def test_latest_returns_newest(self) -> None:
        self.repository.add("first")
        self.repository.add("second")
        latest = self.repository.latest()
        assert latest is not None
        self.assertEqual("second", latest.title)
```

- Use a temporary SQLite file when migrations or file paths matter.
- Skip MySQL or PostgreSQL tests unless the driver and server are available.
- Seed only the rows a test needs, and close sessions.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'mysql'` | `DB_CONNECTION=mysql` without `mysql-connector-python`. | Install the driver, or switch to SQLite for local work. |
| SQLite file named `equipment` in the project root | `DB_DATABASE=equipment` left over from the generated `.env`. | Set `DB_DATABASE=database/database.sqlite`. |
| `ValueError: Unknown queue connection type: ...` from the database | `DB_CONNECTION` does not match a key under `database.connections`. | Use `sqlite`, `mysql`, or `postgresql`. |
| `ValueError: invalid literal for int()` while connecting | Unescaped special characters in credentials. | Percent-encode the value. |
| `NOT NULL constraint failed: todos.id` on SQLite | `BIGINT` primary key; SQLite only auto-increments `INTEGER`. | Use `BigInteger().with_variant(Integer, "sqlite")` in models and migrations. |
| `database is locked` | Open SQLite sessions or connections. | Close sessions promptly; SQLite has limited concurrency. |
| Autogenerate fails or finds nothing | `target_metadata` is `None` or models are not imported in `env.py`. | Import your `Base` and set `target_metadata = Base.metadata`. |

## Best Practices

- Fix `DB_CONNECTION` and `DB_DATABASE` in `.env` before the first database call.
- Install the driver that matches the configured SQLAlchemy dialect.
- Percent-encode credentials and quote their YAML placeholders.
- Use bind parameters for every value in raw SQL.
- Keep one typed declarative `Base` (`DeclarativeBase`, `Mapped[...]`), wire it into `env.py`, and review every autogenerated migration.
- Annotate repositories with `SQLAlchemyFactory` and `Session`, and use the SQLite-safe `BigId` variant for big integer primary keys.
- Keep transactions explicit with `with session, session.begin():` and keep SQLAlchemy calls in repositories.
- Do not commit SQLite files; recreate schema with migrations.
