---
name: "Configuration And Environment Variables"
description: "How Equipment loads .env and config files, interpolates ${VAR:default} values, types them per file format, merges files, and which environment variables the generated project uses."
tags: [equipment, configuration, config, dotenv, env, yaml, json, ini, interpolation, environment-variables, base_path, Configuration, from_value, override, secrets, profiles]
---

# Configuration And Environment Variables

Equipment configuration is a `dependency_injector` `Configuration` provider, `app().config`, filled from the project base path.

## Loading Order

`Equipment.make(base_path)` loads, in this order:

1. `.env` in the base path, if it exists, with `python-dotenv`.
2. `config/*.ini`
3. `config/*.yaml`
4. `config/*.json`
5. `config.base_path`, set to the base path.

The base path is the argument to `app(base_path)`, or the current working directory when no argument is given.

Verified details:

- `.env` values are exported into `os.environ` for the whole process (and its child processes).
- `.env` does not override variables that already exist in the process environment. Real environment variables win.
- Later files deep-merge into earlier ones. A key in `config/*.json` overrides the same key from `config/*.yaml`, while sibling keys survive.
- Files of the same extension are read in `glob` order, which is not sorted. Do not split one top-level key across several files of the same extension.
- Config is read once per container. Restart the process to pick up file or environment changes.

## Interpolation

Values use `${VARIABLE:default}`:

```yaml
app:
  name: ${APP_NAME:Equipment}
  env: ${APP_ENV:local}
```

- `${VAR:default}` uses the environment value, or `default` when the variable is not set.
- `${VAR}` without a default becomes `None` when the variable is not set (verified with YAML).
- Interpolation happens on the file text before parsing, so the substituted text is then parsed as YAML or JSON.

## Value Types Depend On The File Format

The docs say environment values are loaded as strings. Verified behavior is more specific:

| Source line | Loaded value | Type |
|---|---|---|
| YAML `port: ${PORT:8000}` | `8000` | `int` |
| YAML `port: "${PORT:8000}"` | `'8000'` | `str` |
| YAML `flag: ${FLAG:false}` | `False` | `bool` |
| YAML `word: ${WORD:yes}` | `True` | `bool` (YAML 1.1: `yes`, `no`, `on`, `off` are booleans) |
| YAML `zip: ${ZIP:00123}` | `83` | `int` (leading zero is read as octal) |
| YAML `zip: "${ZIP:00123}"` | `'00123'` | `str` |
| YAML `value: ${VALUE:null}` | `None` | `NoneType` |
| JSON `"port": "${PORT:8000}"` | `'8000'` | `str` (placeholders must sit inside JSON strings) |
| JSON `"limit": 10` | `10` | `int` |
| INI `retries = 3` | `'3'` | `str` (the INI section becomes the top-level key) |

Rules that follow:

- Quote YAML placeholders whose value must stay text: passwords, tokens, IDs, codes with leading zeros, versions, and anything that could look like a boolean or number.
- Unquoted YAML values containing `: ` or ` #` can break parsing or be truncated after substitution. Quote them.
- Still cast at the boundary, because the type depends on the file format and quoting: `int(application.config.web.port())`, or inject with `.as_int()`.

```python
port = int(application.config.web.port())
enabled = str(application.config.feature.enabled()).lower() == "true"
```

## Accessing Values

```python
application = app()
application.config.app.name()                      # one value
application.config.notifications.email.sender()    # nested value
application.config.queue.connections.redis()       # a dict
application.config.get("web.port")                 # dotted path
```

Verified pitfalls:

- A missing or misspelled key returns `None`. It does not raise. Use `.required()` when injecting mandatory values.
- Key names that match a public attribute of `dependency_injector`'s `ConfigurationOption` resolve to that attribute instead of your value. Verified examples: `from_env`, `from_value`, `from_dict`, `from_yaml`, `from_json`, `from_ini`, `from_pydantic`, `override`, `reset_override`, `required`, `as_int`, `as_float`, `as_`, `update`, `reset_cache`, `provided`. Others exist, such as `provider`, `overrides`, `overridden`, `related`, `traverse`, and `delegate`. Check with `dir()` before choosing an unusual key. If one already exists, read it through the parent dict: `application.config.section()["from_env"]`.

## File Shape

Give each file one top-level key named after the file:

```yaml
# config/billing.yaml
billing:
  currency: "${BILLING_CURRENCY:EUR}"
  invoice_prefix: "${BILLING_INVOICE_PREFIX:INV}"
```

```python
currency = application.config.billing.currency()
```

Add a new file per service instead of growing `config/app.yaml`. Keep `.env.example` in sync with every variable you introduce, using fake values.

## Generated Config Files

| File | Top-level key | Contents |
|---|---|---|
| `config/app.yaml` | `app` | `name`, `env` |
| `config/database.yaml` | `database` | `connection`, `connections.sqlite`, `connections.mysql`, `connections.postgresql` |
| `config/log.yaml` | `log` | `level`, `channel`, `channels.*`, `formatters.json` |
| `config/queue.yaml` | `queue` | `connection`, `connections.sync`, `connections.redis` |
| `config/storage.yaml` | `storage` | `disk`, `disks.local.path`, `disks.s3.*` |
| `config/web.yaml` | `web` | `host`, `port` |
| `config/inspiring.json` | `inspiring` | `quotes` (example data) |

> The local storage key is `path`, not `root`.

## Environment Variable Reference

| Variable | YAML default | Generated `.env` value | Used by |
|---|---|---|---|
| `APP_NAME` | `Equipment` | `Equipment` | `config/app.yaml`; also the Python logger name |
| `APP_ENV` | `local` | `production` | `config/app.yaml` |
| `LOG_LEVEL` | `debug` | `debug` | `config/log.yaml` |
| `LOG_CHANNEL` | `stack` | `stack` | `config/log.yaml` |
| `DB_CONNECTION` | `sqlite` | `mysql` | `config/database.yaml` |
| `DB_HOST` | `127.0.0.1` | `127.0.0.1` | MySQL and PostgreSQL |
| `DB_PORT` | `3306` or `5432` | `3306` | MySQL and PostgreSQL |
| `DB_DATABASE` | `database/database.sqlite` (SQLite) or `database` | `equipment` | SQLite file path or database name |
| `DB_USERNAME` | `root` | `equipment` | MySQL and PostgreSQL |
| `DB_PASSWORD` | `password` | `equipment` | MySQL and PostgreSQL |
| `DB_CHARSET` | `utf8mb4` | not set | MySQL |
| `QUEUE_CONNECTION` | `sync` | `sync` | `config/queue.yaml` |
| `REDIS_HOST` | `127.0.0.1` | `127.0.0.1` | Redis queue |
| `REDIS_PORT` | `6379` | `6379` | Redis queue |
| `REDIS_DB` | `0` | `0` | Redis queue |
| `REDIS_USERNAME` | `null` | empty | Loaded but not used by the stock Redis code |
| `REDIS_PASSWORD` | `null` | empty | Loaded but not used by the stock Redis code |
| `FILESYSTEM_DISK` | `local` | `local` | `config/storage.yaml` |
| `S3_ENDPOINT` | none | empty | S3 storage |
| `S3_BUCKET` | none | empty | S3 storage |
| `S3_ACCESS_KEY` | none | empty | S3 storage |
| `S3_SECRET_KEY` | none | empty | S3 storage |
| `S3_REGION` | `auto` | not set | S3 storage |
| `S3_PREFIX` | `null` | not set | S3 storage key prefix |
| `WEB_HOST` | `0.0.0.0` | not set | `config/web.yaml` |
| `PORT` | `8000` | not set | `config/web.yaml` |

See `references/project-setup.md` for the recommended local `.env`.

## Environment Profiles

Equipment uses one `config/` directory plus environment variables, not per-environment config directories.

```env
# Local development
APP_ENV=local
LOG_CHANNEL=stack
LOG_LEVEL=debug
DB_CONNECTION=sqlite
DB_DATABASE=database/database.sqlite
QUEUE_CONNECTION=sync
FILESYSTEM_DISK=local
WEB_HOST=127.0.0.1
PORT=8000
```

```env
# Production web process
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
# Production worker process
APP_ENV=production
LOG_CHANNEL=console
LOG_LEVEL=info
DB_CONNECTION=postgresql
QUEUE_CONNECTION=redis
FILESYSTEM_DISK=s3
```

In production, prefer real environment variables or a secret store. A `.env` file is often absent there unless you copy it deliberately.

## Changing Config In Tests

`from_value()` changes the shared container for the rest of the process. Prefer a reversible override:

```python
# Inside a unittest.TestCase method or setUp
self.enterContext(self.app.config.queue.connection.override("sync"))
self.enterContext(self.app.config.storage.disk.override("local"))
```

Do not call `config.override({...})` on the root config: it replaces the whole tree, so every other key reads as `None` until the override is reset.

Override config before creating services that depend on it, or `reset()` those services afterwards. See `references/testing.md`.

## Secrets

- Never commit real secrets to `config/*`, `README.md`, tests, logs, or docs. Keep `.env.example` realistic but fake.
- Quote secret placeholders in YAML so numeric-looking or boolean-looking secrets stay strings.
- Database credentials are inserted into the SQLAlchemy URL without escaping. Percent-encode special characters in the environment value; see `references/database.md`.
- Do not print `.env` contents or full config dumps in logs or chat.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A value is `None` | Missing key, wrong filename or top-level key, or wrong base path. | Check `config/<name>.yaml` defines `<name>:`; run from the project root. |
| A default is ignored | The variable is set in the shell or deployment environment, which beats `.env`. | Inspect the process environment. |
| `TypeError: 'NoneType' object is not subscriptable` at startup | No config was found, usually because the process started outside the project root. | `cd` to the project root or pass `app(base_path)`. |
| A number or boolean where text was expected | Unquoted YAML placeholder. | Quote the placeholder. |
| `TypeError: from_env() takes at least 1 positional argument` (or a method instead of a value) | The key name collides with a config option method, such as `from_env`. | Rename the key, or read it from the parent dict. |
| Production uses local values | A copied `.env`, or missing environment variables in the platform. | Set real variables in the platform; do not ship `.env`. |

## Best Practices

- One top-level key per config file, named after the file.
- Quote YAML placeholders for values that must stay strings; cast or use `.as_int()` at the boundary for numbers.
- Use `.required()` for mandatory settings so typos fail loudly.
- Keep `.env.example` complete and fake; keep `.env` and real secrets out of Git.
- Prefer defaults that let tests run without external services: `sqlite`, `sync`, `local`.
- Use reversible overrides in tests and never override the root config with a partial dict.
