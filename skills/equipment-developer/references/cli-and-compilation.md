---
name: "CLI And Compilation"
description: "Exact behavior of the equipment new and equipment compile commands, including overwrite semantics, exit codes, compiled output contents, and safe compile workflows."
tags: [equipment, cli, click, equipment-new, equipment-compile, bytecode, pyc, py_compile, dist, template, exit-code, overwrite]
---

# CLI And Compilation

Equipment installs one console script, `equipment`, built with Click. It has two commands.

```bash
equipment --help
equipment --version          # e.g. "equipment, version 1.3.0"
python -m equipment --help   # same CLI through the module entry point
```

| Command | Purpose |
|---|---|
| `equipment new NAME` | Create `./NAME` from the maintained project template. |
| `equipment compile DIST` | Compile the current project to `.pyc` files plus runtime assets in `DIST`. |

## `equipment new NAME`

Behavior from `equipment/Command/NewProjectCommand.py`:

1. Uses the current working directory as the parent path.
2. Deletes and recreates a template cache directory, `_project`, inside the installed `equipment/Command/` package directory.
3. Downloads `https://github.com/rogervila/equipment/archive/refs/heads/main.zip` with `requests` (60 second timeout).
4. Extracts it and uses `equipment-main/project` as the template.
5. If `./NAME` exists, asks `Directory "..." already exists. Do you want to override it? [y/N]`.
6. Copies the template into `./NAME`, ignoring `*.py[co]`, `__pycache__`, `.git`, `htmlcov`, `equipment`, `venv`, `.env`, `.coverage`, `*.log`, `*.lock`, `*.sqlite*`, and `.DS_Store`.
7. Copies `.env.example` to `.env`.
8. Replaces the text `PROJECT_NAME` with `NAME` in the generated `pyproject.toml`.

Consequences:

- The template always comes from the `main` branch, not from the installed package version.
- The installed package directory must be writable, because the template cache lives there.
- Network access to GitHub is required. In restricted networks, generate the project elsewhere and copy it, or vendor the template internally.
- There are no options or feature flags. Remove unused files after generation.

### Overwrite Semantics

Verified behavior when `./NAME` already exists:

| Answer | Result |
|---|---|
| `n` or Enter | Prints `Skip`. Nothing changes. |
| No stdin (non-interactive) | Prints `Fatal error:` and nothing changes. |
| `y` | Merges the template over the directory. Template files are replaced, including `app/__init__.py` and `.env` (overwritten from `.env.example`). Files that are not in the template are kept. |

> Never run `equipment new` against an existing project directory and never answer `y` for a project with real work in it. It silently replaces your container, entry points, config, tests, and `.env`. Generate into a new directory and diff instead.

### Exit Codes

The command catches broad exceptions, prints a red message, and returns. Verified: the process exits with code `0` after a download failure, a declined overwrite, and a non-interactive abort.

Automation must check the result, not the exit code:

```bash
equipment new billing-api
test -f billing-api/pyproject.toml || { echo "equipment new failed"; exit 1; }
```

```powershell
equipment new billing-api
if (-not (Test-Path billing-api/pyproject.toml)) { throw "equipment new failed" }
```

### Common Failures

| Message | Cause | Fix |
|---|---|---|
| `Could not download project template: ...` | No network or proxy access to GitHub. | Fix connectivity, or copy a project generated elsewhere. |
| `Project template not found in ...` | The archive layout changed or the download was not the expected ZIP. | Retry; report upstream if it persists. |
| `Fatal error: ...` | Copy or write failure, or an aborted prompt. | Check permissions and target directory; run interactively. |
| `equipment: command not found` | Scripts directory not on `PATH`. | Use `python -m equipment ...`, a virtual environment, or `pipx`. |

## `equipment compile DIST`

Behavior from `equipment/Command/CompileCommand.py`:

1. Walks the current directory with `os.walk('.')`.
2. Skips only directories named `__pycache__`, `dist`, `tests`, or `equipment`, and the resolved output directory.
3. Compiles every other `*.py` file with `py_compile` to `DIST/<same relative path>c`.
4. Copies these paths when they exist: `config/`, `database/`, `storage/`, `.coveragerc`, `.editorconfig`, `.env`, `.env.example`, `.gitignore`, `pyproject.toml`, `README.md`.
5. Prints `Project successfully compiled on DIST!`.

Run it from the generated project root:

```bash
equipment compile dist
cd dist
python main.pyc
```

```bat
equipment compile dist
cd dist
py -3.14 main.pyc
```

### What Ends Up In The Output

Verified on a generated project:

- An in-project virtual environment is compiled. With `.venv/` inside the project, the output contained `dist/.venv/` with 6,702 `.pyc` files (120 MB), and the command took 36 seconds.
- A setuptools `build/` directory (created by `python -m pip install .`) is compiled into `dist/build/`.
- `.env` is copied as-is, including secrets and the generated `APP_ENV=production` and `DB_CONNECTION=mysql` values.
- `storage/` is copied with its contents, including local files and `storage/logs/*.log`.
- `database/` is copied, including any local `*.sqlite` file.
- Stale files in `DIST` are not removed.
- Third-party dependencies are not bundled. The target needs `python -m pip install .` (or equivalent) with a compatible interpreter.

### Safe Compile Workflow

```bash
# From the project root, with the virtual environment OUTSIDE the project
rm -rf dist build
python -m unittest
python -m equipment compile dist
# Review what will ship
ls -A dist
# Replace or remove local-only runtime files before shipping
rm -f dist/.env dist/database/*.sqlite* dist/storage/logs/*.log
cd dist
python main.pyc
```

On Windows PowerShell, use `Remove-Item -Recurse -Force dist, build` and `Remove-Item dist\.env` instead of `rm`.

If the virtual environment must live in the project, compile from a clean copy (for example a fresh `git clone` or an exported archive) instead of the working tree.

### Limits

- Bytecode is not a security boundary. `.pyc` files are easy to decompile.
- `.pyc` files are specific to the Python minor version. Build with the same Python version the target will run.
- Compile output does not replace packaging, containers, or deployment automation.
- Run compiled entry points from inside the output directory (`cd dist`), because `app()` uses the working directory as the base path.

## Best Practices

- Never point `equipment new` at an existing project. Generate into a new directory and compare.
- Check for `NAME/pyproject.toml` after `equipment new` in scripts; do not trust the exit code.
- Delete `dist` and `build` before compiling, and keep virtual environments out of the project tree.
- Review `dist/.env`, `dist/storage/`, and `dist/database/` before shipping compiled output.
- Smoke test with `cd dist && python main.pyc` using the target Python version.
- Use `python -m equipment ...` when the console script is not on `PATH`.
