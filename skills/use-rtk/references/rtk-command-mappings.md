---
name: "RTK Command Mappings"
description: "Complete mapping of native terminal commands to their RTK equivalents, organized by ecosystem, with flags and usage notes."
tags: [rtk, command-mapping, git, cargo, pytest, jest, vitest, phpunit, docker, kubectl, npm, pnpm, bun, tsc, eslint, prettier, mypy, ruff, go, ruby, java, maven, dotnet, grep, find, ls]
---

# RTK Command Mappings

Use the table for your ecosystem to pick the correct RTK subcommand before running any terminal command. If a command is not listed, use `rtk rewrite <command>` to check for a rewrite, or wrap it with `rtk test`, `rtk err`, or `rtk summary`.

## Decision Flow

1. Is the command in the tables below? → Use the RTK form.
2. Unsure? → `rtk rewrite <the command>` and follow its output.
3. No RTK form exists? → Run the command unchanged.
4. RTK output was unusable? → `rtk bypass <the command>`.

## File System Commands

| Native command | RTK command | Notes |
|---|---|---|
| `ls [path]` | `rtk ls [path]` | Accepts native `ls` flags |
| `ls -R [path]` | `rtk ls -R [path]` | Deep listing is heavily compacted |
| `tree [path]` | `rtk tree [path]` | Compact tree shape |
| `cat <file>` | `rtk read <file>` | Intelligent filtering; use `--level minimal` or `--level aggressive` for larger files |
| `cat <f1> <f2>` | `rtk read <f1> <f2>` | Supports multiple files |
| `find [flags]` | `rtk find [flags]` | Accepts native `find` flags like `-name`, `-type` |
| `grep [flags]` | `rtk grep [flags]` | Compact: strips whitespace, truncates, groups by file |
| `rg [flags]` | `rtk rg [flags]` | Same compact filter as `rtk grep` |
| `ast-grep [flags]` | `rtk ast-grep [flags]` | Groups matches by file |
| `wc [flags]` | `rtk wc [flags]` | Strips paths and padding |
| `diff [args]` | `rtk diff [args]` | Ultra-condensed: only changed lines |

### `rtk read` Flags

| Flag | Meaning |
|---|---|
| `--level none` | Full content (default) |
| `--level minimal` | Light filtering |
| `--level aggressive` | Heavy filtering for large files |
| `--max-lines N` | Structural preview capped at N lines (keeps signatures and imports; not first N lines) |
| `--head-lines N` | Keep only the first N lines |
| `--tail-lines N` | Keep only the last N lines |
| `--line-numbers` | Show line numbers |

## Git And Version Control

| Native command | RTK command | Notes |
|---|---|---|
| `git status` | `rtk git status` | |
| `git diff` | `rtk git diff` | |
| `git log` | `rtk git log` | |
| `git [any]` | `rtk git [any]` | All git subcommands pass through RTK's git filter |
| `gh [any]` | `rtk gh [any]` | GitHub CLI |
| `glab [any]` | `rtk glab [any]` | GitLab CLI |
| `gt [any]` | `rtk gt [any]` | Graphite stacked PRs |

## JavaScript / TypeScript

| Native command | RTK command | Notes |
|---|---|---|
| `npm run <script>` | `rtk npm <script>` | Strips boilerplate |
| `npx tsc [args]` | `rtk npx tsc [args]` | Auto-routed to specialized tsc filter |
| `npx eslint [args]` | `rtk npx eslint [args]` | Auto-routed to lint filter |
| `npx prisma [cmd]` | `rtk npx prisma [cmd]` | Auto-routed to prisma filter |
| `npx [other]` | `rtk npx [other]` | Intelligent routing |
| `pnpm [cmd]` | `rtk pnpm [cmd]` | Ultra-compact |
| `yarn [cmd]` | `rtk npm [cmd]` or `rtk pnpm [cmd]` | Use whichever matches the project's package manager |
| `bun [cmd]` | `rtk bun [cmd]` | |
| `bunx [tool]` | `rtk bunx [tool]` | Passthrough + auto-filter |
| `tsc [args]` | `rtk tsc [args]` | Grouped error output |
| `eslint [args]` | `rtk lint [args]` | Grouped rule violations |
| `prettier [args]` | `rtk prettier [args]` | Compact format check output |
| `jest [args]` | `rtk jest [args]` | Shows only failures |
| `vitest [args]` | `rtk vitest [args]` | Shows only failures |
| `playwright [args]` | `rtk playwright [args]` | Compact E2E output |
| `next build` | `rtk next build` | Compact build output |
| `ng build` | `rtk ng build` | Compact table output |
| `ng test` | `rtk ng test` | |
| `prisma [cmd]` | `rtk prisma [cmd]` | Strips ASCII art |
| `deno [cmd]` | `rtk deno [cmd]` | |

## Python

| Native command | RTK command | Notes |
|---|---|---|
| `pytest [args]` | `rtk pytest [args]` | Shows only failures |
| `python -m pytest [args]` | `rtk pytest [args]` | Equivalent |
| `mypy [args]` | `rtk mypy [args]` | Grouped error output |
| `ruff check [args]` | `rtk ruff check [args]` | Compact linter output |
| `ruff format [args]` | `rtk ruff format [args]` | |
| `pip [args]` | `rtk pip [args]` | Auto-detects uv |
| `pip install [args]` | `rtk pip install [args]` | Strips progress bars and boilerplate |
| `uv run [cmd]` | `rtk uv [cmd]` | Preserves uv-managed environment semantics |

## Rust

| Native command | RTK command | Notes |
|---|---|---|
| `cargo test [args]` | `rtk cargo test [args]` | Shows only failures |
| `cargo build [args]` | `rtk cargo build [args]` | Compact build output |
| `cargo check [args]` | `rtk cargo check [args]` | |
| `cargo clippy [args]` | `rtk cargo clippy [args]` | |
| `cargo [any]` | `rtk cargo [any]` | All cargo subcommands |

## Go

| Native command | RTK command | Notes |
|---|---|---|
| `go test [args]` | `rtk go test [args]` | Shows only failures |
| `go build [args]` | `rtk go build [args]` | |
| `go [any]` | `rtk go [any]` | All go subcommands |
| `golangci-lint run` | `rtk golangci-lint run` | Compact lint output |
| `golangci-lint [other]` | `rtk golangci-lint [other]` | Passes through for other invocations |

## PHP

| Native command | RTK command | Notes |
|---|---|---|
| `php artisan [cmd]` | `rtk php artisan [cmd]` | Compact artisan output |
| `php -l [file]` | `rtk php -l [file]` | Compact syntax check output |
| `./vendor/bin/phpunit [args]` | `rtk phpunit [args]` | Shows only failures |
| `./vendor/bin/phpstan analyse` | `rtk phpstan analyse` | Compact static analysis output |
| `./vendor/bin/pest [args]` | `rtk pest [args]` | Shows only failures |
| `./vendor/bin/paratest [args]` | `rtk paratest [args]` | Compact parallel test output |
| `./vendor/bin/ecs check` | `rtk ecs check` | Compact code style output |
| `./vendor/bin/ecs fix` | `rtk ecs fix` | |
| `./vendor/bin/pint [args]` | `rtk pint [args]` | Compact PHP-CS-Fixer output |
| `php run-tests.php [args]` | `rtk phpt [args]` | Compact .phpt summary |

## Ruby / Rails

| Native command | RTK command | Notes |
|---|---|---|
| `bundle exec rspec [args]` | `rtk rspec [args]` | Compact RSpec output |
| `bundle exec rubocop [args]` | `rtk rubocop [args]` | Compact linter output |
| `rake test [args]` | `rtk rake [args]` | Compact Minitest output |
| `bundle exec rake [args]` | `rtk rake [args]` | |

## Java / JVM / Scala

| Native command | RTK command | Notes |
|---|---|---|
| `mvn [cmd]` | `rtk mvn [cmd]` | Compact Maven output |
| `./mvnw [cmd]` | `rtk mvn [cmd]` | Compact Maven wrapper output |
| `mvnd [cmd]` | `rtk mvnd [cmd]` | Same filters as `rtk mvn` |
| `sbt [cmd]` | `rtk sbt [cmd]` | Compact SBT output |
| `./gradlew build` | `rtk gradlew build` | Compact Gradle build output |
| `./gradlew test` | `rtk gradlew test` | Compact Gradle test output |
| `./gradlew lint` | `rtk gradlew lint` | |
| `ctest [args]` | `rtk ctest [args]` | |

## .NET

| Native command | RTK command | Notes |
|---|---|---|
| `dotnet build [args]` | `rtk dotnet build [args]` | Compact build output |
| `dotnet test [args]` | `rtk dotnet test [args]` | Shows only failures |
| `dotnet restore [args]` | `rtk dotnet restore [args]` | |
| `dotnet format [args]` | `rtk dotnet format [args]` | |

## Infrastructure

| Native command | RTK command | Notes |
|---|---|---|
| `docker [cmd]` | `rtk docker [cmd]` | Compact docker output |
| `kubectl [cmd]` | `rtk kubectl [cmd]` | Compact kubectl output |
| `oc [cmd]` | `rtk oc [cmd]` | OpenShift CLI compact output |
| `aws [cmd]` | `rtk aws [cmd]` | Forces JSON, compresses output |

## Databases

| Native command | RTK command | Notes |
|---|---|---|
| `psql [args]` | `rtk psql [args]` | Strips borders, compresses tables |
| `sqlfluff lint [args]` | `rtk sqlfluff lint [args]` | Compact SQL linter output |
| `sqlfluff fix [args]` | `rtk sqlfluff fix [args]` | |

## Network

| Native command | RTK command | Notes |
|---|---|---|
| `curl [args]` | `rtk curl [args]` | Auto-JSON detection and schema output |
| `wget [args]` | `rtk wget [args]` | Strips progress bars |

## General-Purpose Wrappers

When no specific RTK subcommand exists, use these fallback wrappers.

| Wrapper | Use when |
|---|---|
| `rtk test <full-command>` | Running any test suite — shows only failures |
| `rtk err <full-command>` | Running any command — shows only errors and warnings |
| `rtk summary <full-command>` | Any command — heuristic summary |
| `<cmd> 2>&1 \| rtk pipe -f <filter>` | Piping output through a named RTK filter |

### Named Filters For `rtk pipe`

Pass these to `--filter`:

- `cargo-test`
- `pytest`
- `phpunit`
- `phpstan`
- `pint`
- `grep`
- `find`
- `git-log`

Example:

```bash
cargo test 2>&1 | rtk pipe -f cargo-test
```

## Bypass And Recovery

| Command | Use when |
|---|---|
| `rtk bypass <command>` | The filtered output was empty, garbled, or contradicted the exit code — re-runs without filtering but still tracks usage |
| `rtk recall <hash>` | Recalls the full output elided by a filter, using the content hash from RTK's recovery hint |
| `rtk recall --list` | Lists all stored entries available for recall |

### When To Use `rtk bypass`

Only use `rtk bypass` when the RTK output was **genuinely unusable**:

- Output was empty but output was clearly expected.
- Output contradicted the exit code.
- Output was garbled or malformed.

Do not use `rtk bypass` as a default. Prefer filtered output and use `rtk recall <hash>` when specific elided content is needed.

## Checking For RTK Rewrites

Before running any unfamiliar command, use `rtk rewrite` to verify whether RTK has a rewrite for it:

```bash
rtk rewrite "git status"
# → rtk git status   (exit 0: safe to use)

rtk rewrite "some-custom-tool --verbose"
# → (no output, exit 1: run unchanged)
```

## Best Practices

- Check this table first before running any command when RTK is available.
- Use `rtk read` instead of `cat` for all file reads during LLM-assisted coding sessions.
- Use `rtk grep` or `rtk rg` instead of `grep` or `rg` for all file searches.
- Use `rtk git diff` instead of `git diff` for all diff operations — the condensed form saves the most tokens on large diffs.
- Use `rtk test <cmd>` for any test runner not listed above — failures-only output is nearly always what the LLM needs.
- Use `rtk err <cmd>` for build tools not listed above — errors-only output keeps context lean.
