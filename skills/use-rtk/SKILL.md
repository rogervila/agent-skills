---
name: use-rtk
description: Tells LLMs to use RTK (Rust Token Killer) when the rtk command is available, reducing LLM token consumption by 60-90% through transparent command output filtering and summarization.
license: MIT
metadata:
  author: "Roger Vilà"
  repository: "https://github.com/rogervila/agent-skills"
  version: "1.0.0"
  keywords: "rtk, rust-token-killer, token-optimization, token-reduction, cli-proxy, llm-efficiency, command-output, filtering, git, cargo, pytest, phpunit, jest, vitest, docker, kubectl"
---

# Use RTK (Rust Token Killer)

When the `rtk` command is available in the environment, use it to wrap terminal commands. RTK is a high-performance CLI proxy that filters and summarizes command output before it reaches the LLM context, reducing token consumption by 60–90% with no change to workflow or results.

## Activation Criteria

Activate this skill whenever:

- The `rtk` command is available (check with `which rtk` or `rtk --version`).
- You are about to run a command whose output could be long, repetitive, or boilerplate-heavy.
- The task involves git operations, running tests, linting, building, reading files, searching files, inspecting dependencies, or inspecting logs.

Do not use RTK for:

- Commands whose full raw output is intentionally needed by the user (e.g., interactive terminal programs, user-facing output scripts).
- Commands that have no RTK equivalent and where passing to `rtk bypass` would add no value.
- Shell constructs that RTK cannot rewrite: subshell substitutions (`$(...)`) and file redirects. Run these unchanged.

## Decision Rule: Before Running Any Command

Before running any command, check whether RTK has a subcommand or proxy for it.

If yes → use the RTK form.
If unsure → run `rtk rewrite <command>` to ask RTK whether a rewrite exists.
If no RTK equivalent → run the command unchanged.
If the output would be unusable (empty when output was expected, contradicting exit code, or garbled) → re-run as `rtk bypass <command>`.

## Core Command Mappings

Use these RTK subcommands instead of their native equivalents.

### File System

| Instead of | Use |
|---|---|
| `ls [path]` | `rtk ls [path]` |
| `find [args]` | `rtk find [args]` |
| `tree [path]` | `rtk tree [path]` |
| `cat [file]` | `rtk read [file]` |
| `grep [args]` | `rtk grep [args]` |
| `rg [args]` | `rtk rg [args]` |

### Git

| Instead of | Use |
|---|---|
| `git [subcommand]` | `rtk git [subcommand]` |
| `gh [subcommand]` | `rtk gh [subcommand]` |
| `glab [subcommand]` | `rtk glab [subcommand]` |
| `gt [subcommand]` | `rtk gt [subcommand]` |

### JavaScript / TypeScript

| Instead of | Use |
|---|---|
| `npm run [script]` | `rtk npm [script]` |
| `npx [tool]` | `rtk npx [tool]` |
| `pnpm [cmd]` | `rtk pnpm [cmd]` |
| `yarn [cmd]` | (use `rtk npm` or `rtk pnpm` as applicable) |
| `bun [cmd]` | `rtk bun [cmd]` |
| `bunx [tool]` | `rtk bunx [tool]` |
| `tsc [args]` | `rtk tsc [args]` |
| `eslint [args]` | `rtk lint [args]` |
| `prettier [args]` | `rtk prettier [args]` |
| `jest [args]` | `rtk jest [args]` |
| `vitest [args]` | `rtk vitest [args]` |
| `next build` | `rtk next build` |
| `ng build/test` | `rtk ng build` / `rtk ng test` |
| `npx prisma [cmd]` | `rtk prisma [cmd]` |

### Python

| Instead of | Use |
|---|---|
| `pytest [args]` | `rtk pytest [args]` |
| `mypy [args]` | `rtk mypy [args]` |
| `ruff [args]` | `rtk ruff [args]` |
| `pip [args]` | `rtk pip [args]` |
| `uv run [cmd]` | `rtk uv [cmd]` |

### Rust

| Instead of | Use |
|---|---|
| `cargo [subcommand]` | `rtk cargo [subcommand]` |

### Go

| Instead of | Use |
|---|---|
| `go [cmd]` | `rtk go [cmd]` |
| `golangci-lint run` | `rtk golangci-lint run` |

### PHP

| Instead of | Use |
|---|---|
| `php [cmd]` | `rtk php [cmd]` |
| `./vendor/bin/phpunit` | `rtk phpunit [args]` |
| `./vendor/bin/phpstan` | `rtk phpstan [args]` |
| `./vendor/bin/pint` | `rtk pint [args]` |
| `./vendor/bin/pest` | `rtk pest [args]` |
| `./vendor/bin/paratest` | `rtk paratest [args]` |
| `./vendor/bin/ecs` | `rtk ecs [args]` |

### Ruby / Rails

| Instead of | Use |
|---|---|
| `bundle exec rspec` | `rtk rspec [args]` |
| `bundle exec rubocop` | `rtk rubocop [args]` |
| `rake test` | `rtk rake [args]` |

### Java / JVM

| Instead of | Use |
|---|---|
| `./mvnw [cmd]` / `mvn [cmd]` | `rtk mvn [cmd]` |
| `mvnd [cmd]` | `rtk mvnd [cmd]` |
| `sbt [cmd]` | `rtk sbt [cmd]` |
| `./gradlew [cmd]` | `rtk gradlew [cmd]` |

### .NET

| Instead of | Use |
|---|---|
| `dotnet [cmd]` | `rtk dotnet [cmd]` |
| `ctest [args]` | `rtk ctest [args]` |

### Infrastructure

| Instead of | Use |
|---|---|
| `docker [cmd]` | `rtk docker [cmd]` |
| `kubectl [cmd]` | `rtk kubectl [cmd]` |
| `oc [cmd]` | `rtk oc [cmd]` |
| `aws [cmd]` | `rtk aws [cmd]` |
| `psql [args]` | `rtk psql [args]` |

### SQL Linting

| Instead of | Use |
|---|---|
| `sqlfluff [args]` | `rtk sqlfluff [args]` |

### Other

| Instead of | Use |
|---|---|
| `curl [args]` | `rtk curl [args]` |
| `wget [args]` | `rtk wget [args]` |
| `wc [args]` | `rtk wc [args]` |
| `playwright [args]` | `rtk playwright [args]` |
| `deno [cmd]` | `rtk deno [cmd]` |
| `ast-grep [args]` | `rtk ast-grep [args]` |

## General-Purpose RTK Wrappers

When no specific RTK subcommand exists for a command, use one of these general wrappers:

| Wrapper | When to use |
|---|---|
| `rtk test <full-test-command>` | Run any test command and show only failures |
| `rtk err <full-command>` | Run any command and show only errors and warnings |
| `rtk summary <full-command>` | Run any command and show a heuristic summary |
| `rtk pipe -f <filter>` | Pipe stdin through a named filter (e.g., `cargo test 2>&1 \| rtk pipe -f cargo-test`) |

### Pipe Mode (stdin)

RTK can filter stdin in Unix pipe mode. Named filters include: `cargo-test`, `pytest`, `phpunit`, `phpstan`, `pint`, `grep`, `find`, `git-log`.

Example:

```bash
cargo test 2>&1 | rtk pipe -f cargo-test
```

## Recovering Filtered Output

RTK condenses output. If the condensed result is unusable:

1. Re-run as `rtk bypass <command>` — executes without filtering, but still tracks usage.
2. Use `rtk recall <hash>` — retrieves full output elided by a filter using the content hash shown in RTK's recovery hint.

```bash
# Re-run without filtering
rtk bypass cargo test

# Recall what a filter elided (hash from the RTK recovery hint)
rtk recall abc123
```

## Verifying RTK Rewrites

Use `rtk rewrite <command>` to check how RTK would rewrite a specific command before running it. This is the single source of truth for hook rewrites.

```bash
rtk rewrite "git status"
# → rtk git status

rtk rewrite "cargo test --workspace"
# → rtk cargo --workspace test  (or equivalent)
```

Exit codes from `rtk rewrite`:

| Code | Meaning |
|---|---|
| `0` | Rewrite printed; allow rules cover every command — safe to auto-allow. |
| `1` | No rewrite available — run the command unchanged. |
| `2` | A deny rule matched — block the command. |
| `3` | Rewrite printed; ask rule matched or allow rules do not cover every command — use the rewrite but defer approval to the host. |

## Token Savings Tracking

After tasks involving RTK, check savings if relevant:

```bash
# Global token savings summary
rtk gain

# Current project only
rtk gain --project

# Day-by-day breakdown
rtk gain --daily

# Weekly breakdown
rtk gain --weekly

# Discover commands that ran outside RTK (missed optimizations)
rtk discover

# RTK adoption across sessions
rtk session
```

## Initialization (One-Time Setup)

If RTK is installed but not yet initialized for the current AI assistant environment, run:

```bash
# Initialize globally for the current assistant (e.g., antigravity)
rtk init -g --agent antigravity

# Preview what would change without writing files
rtk init --dry-run

# Verify hook integrity after setup
rtk verify
```

Supported agents for `--agent`: `claude`, `cursor`, `trae`, `windsurf`, `cline`, `kilocode`, `antigravity`, `kimi`, `pi`, `hermes`, `droid`, `vibe`, `omp`.

## LLM Proxy (Optional Advanced Feature)

RTK includes a transparent LLM proxy that intercepts and compresses input tokens in the LLM request itself, not just command output. This is separate from the hook-based output filtering.

```bash
# Check proxy availability
rtk llm-proxy setup

# Start the proxy daemon
rtk llm-proxy start

# Check proxy status
rtk llm-proxy status

# Stop the proxy
rtk llm-proxy stop
```

## Pipeline Inspection

To inspect, validate, or test the RTK compression pipeline:

```bash
# Show the resolved pipeline
rtk pipeline show

# Validate all pipeline files
rtk pipeline validate

# Explain what fires for a given command
rtk pipeline explain
```

## Quick Start Workflow

1. **Check RTK availability**: `which rtk` or `rtk --version`.
2. **Before running a command**: look up the RTK subcommand in the mappings above, or run `rtk rewrite <command>` to confirm.
3. **Run using the RTK form**: e.g., `rtk git status` instead of `git status`.
4. **If output is unusable**: re-run with `rtk bypass <command>` or `rtk recall <hash>`.
5. **Track savings**: `rtk gain` after completing a task if savings reporting is relevant.

## Non-Goals And Anti-patterns

- Do not use RTK for commands where the full output is the artifact (e.g., generating a file with output redirection).
- Do not use RTK in scripts or CI pipelines that consumers depend on for exact, parseable output — RTK is for LLM context, not downstream parsing.
- Do not re-run `rtk bypass` unnecessarily. Use it only when the filtered output was genuinely unusable.
- Do not install or re-initialize RTK if it is already installed and the hooks are active.

## Reference Documentation

- [RTK Overview And Usage](references/rtk-overview.md) — What RTK is, how it works, all subcommands with descriptions, installation, and initialization.
- [RTK Command Mappings](references/rtk-command-mappings.md) — Complete mapping of native commands to RTK equivalents, organized by ecosystem.
- [RTK Advanced Features](references/rtk-advanced-features.md) — Pipeline system, LLM proxy, plugin authoring, token analytics, and bypass/recall recovery.

## License

This skill is licensed under the [MIT License](../../LICENSE).
