---
name: "RTK Overview And Usage"
description: "What RTK (Rust Token Killer) is, how it works, all subcommands with descriptions, installation, and initialization."
tags: [rtk, rust-token-killer, token-optimization, cli-proxy, installation, initialization, subcommands, llm-efficiency]
---

# RTK Overview And Usage

Last checked: 2026-11-03.

RTK (Rust Token Killer) is an open-source CLI proxy that filters and summarizes terminal command output before it reaches the LLM context window, reducing token consumption by 60–90% with zero change to the agent's workflow or accuracy.

Source repository: https://github.com/rtk-ai/rtk

## What Problem RTK Solves

AI coding agents read the full output of every command they run. Routine commands produce large volumes of boilerplate output that the agent must process:

- `git status` / `git diff` — dozens of lines including unchanged paths, mode lines, and index headers.
- `cargo test` / `pytest` / `phpunit` — hundreds of lines of passing test output when only failures matter.
- `ls -R` / `find` — deep recursive file listings with paths the LLM ignores.
- `npm install` / `pip install` — progress bars, progress spinners, and download summaries.

RTK intercepts these outputs and passes only a concise signal back to the LLM: failures, errors, the file tree shape, the relevant diff lines. The agent sees less noise and costs less.

## How RTK Works

RTK is a single Rust binary with zero runtime dependencies. It:

1. **Intercepts** the command before it runs (via a hook registered with the AI agent, or by direct invocation as `rtk <subcommand>`).
2. **Runs** the native command internally.
3. **Filters and summarizes** the output using per-tool compression rules (smart filtering, error grouping, truncation, deduplication).
4. **Returns** the compressed output to the LLM's context.

RTK tracks input tokens, output tokens, and savings per command in a local database, accessible via `rtk gain`.

## Version

RTK version in this environment: **1.1.0**

Check the installed version with:

```bash
rtk --version
```

## Installation

> Install `rtk-ai/rtk`, not any unrelated package also named `rtk`.

### Linux and macOS (Quick Install)

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh
```

### Homebrew (macOS and Linux)

```bash
brew install rtk-ai/tap/rtk
```

### Windows (WinGet)

```powershell
winget install rtk-ai.rtk
```

### Cargo (from source, avoiding name collisions)

```bash
cargo install --git https://github.com/rtk-ai/rtk --branch master rtk
```

## Initialization

After installing, initialize RTK for the AI assistant environment. This registers the hook that allows RTK to transparently rewrite commands before the agent runs them.

```bash
# Initialize globally for a specific agent
rtk init -g --agent antigravity   # Google Antigravity
rtk init -g --agent claude        # Claude Code (default)
rtk init -g --agent cursor        # Cursor
rtk init -g --agent windsurf      # Windsurf
rtk init -g --agent cline         # Cline / Roo Code
rtk init -g --agent trae          # Trae IDE
rtk init -g --agent kilocode      # Kilo Code
rtk init -g --agent kimi          # Kimi AI
rtk init -g --agent pi            # Pi coding agent
rtk init -g --agent hermes        # Hermes CLI
rtk init -g --agent droid         # Factory Droid CLI
rtk init -g --agent vibe          # Mistral Vibe CLI
rtk init -g --agent omp           # Oh My Pi (OMP)

# Preview changes without writing files
rtk init --dry-run

# Preview changes with content shown
rtk init --dry-run -v

# Hook only (skip RTK.md injection)
rtk init -g --hook-only

# Apply changes without prompting
rtk init -g --auto-patch

# Verify hook integrity after setup
rtk verify

# Uninstall
rtk init --uninstall
```

The `-g` flag installs into the global assistant config directory rather than a local project file.

## Complete Subcommand Reference

All subcommands available in RTK 1.1.0:

### File System

| Subcommand | Description |
|---|---|
| `rtk ls [paths...]` | List directory contents with token-optimized output (proxy to native `ls`) |
| `rtk tree [path]` | Directory tree with token-optimized output (proxy to native `tree`) |
| `rtk read <files...>` | Read file(s) with intelligent filtering. Flags: `--level`, `--max-lines`, `--head-lines`, `--tail-lines`, `--line-numbers` |
| `rtk find [flags]` | Find files with compact tree output; accepts native `find` flags such as `-name`, `-type` |
| `rtk grep [args]` | Compact grep — strips whitespace, truncates, groups by file |
| `rtk rg [args]` | Compact ripgrep — runs `rg` natively, same output filter as `rtk grep` |
| `rtk ast-grep [args]` | Compact ast-grep — runs `ast-grep` natively, groups matches by file |
| `rtk wc [args]` | Word/line/byte count with compact output (strips paths and padding) |
| `rtk diff [args]` | Ultra-condensed diff (only changed lines) |

### Version Control

| Subcommand | Description |
|---|---|
| `rtk git [subcommand]` | Git commands with compact output |
| `rtk gh [subcommand]` | GitHub CLI (`gh`) commands with token-optimized output |
| `rtk glab [subcommand]` | GitLab CLI (`glab`) commands with token-optimized output |
| `rtk gt [subcommand]` | Graphite (`gt`) stacked PR commands with compact output |

### JavaScript / TypeScript

| Subcommand | Description |
|---|---|
| `rtk npm [script]` | npm run with filtered output (strip boilerplate) |
| `rtk npx [tool]` | npx with intelligent routing (tsc, eslint, prisma → specialized filters) |
| `rtk pnpm [cmd]` | pnpm commands with ultra-compact output |
| `rtk bun [cmd]` | Bun runtime commands with compact output |
| `rtk bunx [tool]` | bunx with passthrough + auto-filter |
| `rtk tsc [args]` | TypeScript compiler with grouped error output |
| `rtk lint [args]` | ESLint with grouped rule violations |
| `rtk prettier [args]` | Prettier format checker with compact output |
| `rtk format [args]` | Universal format checker (prettier, black, ruff format) |
| `rtk jest [args]` | Jest commands with compact output |
| `rtk vitest [args]` | Vitest commands with compact output |
| `rtk next [cmd]` | Next.js build with compact output |
| `rtk ng [cmd]` | Angular build with compact tables; other commands pass through |
| `rtk prisma [cmd]` | Prisma commands with compact output (no ASCII art) |
| `rtk playwright [args]` | Playwright E2E tests with compact output |
| `rtk deno [cmd]` | Deno runtime commands with compact output |

### Python

| Subcommand | Description |
|---|---|
| `rtk pytest [args]` | Pytest test runner with compact output |
| `rtk mypy [args]` | Mypy type checker with grouped error output |
| `rtk ruff [args]` | Ruff linter/formatter with compact output |
| `rtk pip [args]` | Pip package manager with compact output (auto-detects uv) |
| `rtk uv [cmd]` | uv run with compact output while preserving uv-managed environment semantics |

### Rust

| Subcommand | Description |
|---|---|
| `rtk cargo [subcommand]` | Cargo commands with compact output |

### Go

| Subcommand | Description |
|---|---|
| `rtk go [cmd]` | Go commands with compact output |
| `rtk golangci-lint [cmd]` | golangci-lint wrapper with compact `run` support and passthrough for other invocations |

### PHP

| Subcommand | Description |
|---|---|
| `rtk php [cmd]` | PHP command runner with compact output for artisan and syntax checks |
| `rtk phpunit [args]` | PHPUnit test runner with compact output |
| `rtk phpstan [args]` | PHPStan analyzer with compact output |
| `rtk pest [args]` | Pest test runner with compact output |
| `rtk paratest [args]` | ParaTest parallel test runner with compact output |
| `rtk ecs [args]` | EasyCodingStandard (ECS) code style fixer with compact output |
| `rtk pint [args]` | Laravel Pint (PHP-CS-Fixer) code style fixer with compact output |
| `rtk phpt [args]` | PHP run-tests.php (.phpt) with compact summary and failure diffs |

### Ruby / Rails

| Subcommand | Description |
|---|---|
| `rtk rspec [args]` | RSpec test runner with compact output (Rails/Ruby) |
| `rtk rubocop [args]` | RuboCop linter with compact output (Ruby) |
| `rtk rake [args]` | Rake/Rails test with compact Minitest output (Ruby) |

### Java / JVM / Scala

| Subcommand | Description |
|---|---|
| `rtk mvn [cmd]` | Apache Maven wrapper with compact output (test, integration-test, compile, package, install, verify, deploy) |
| `rtk mvnd [cmd]` | Maven Daemon (mvnd) with compact output — same filters as `rtk mvn` |
| `rtk sbt [cmd]` | SBT (Scala Build Tool) commands with compact output |
| `rtk gradlew [cmd]` | Android Gradle wrapper with compact output (build, test, lint) |
| `rtk ctest [args]` | CTest with compact output |

### .NET

| Subcommand | Description |
|---|---|
| `rtk dotnet [cmd]` | .NET commands with compact output (build/test/restore/format) |

### SQL

| Subcommand | Description |
|---|---|
| `rtk psql [args]` | PostgreSQL client with compact output (strip borders, compress tables) |
| `rtk sqlfluff [args]` | SQLFluff SQL linter with compact output |

### Infrastructure

| Subcommand | Description |
|---|---|
| `rtk docker [cmd]` | Docker commands with compact output |
| `rtk kubectl [cmd]` | Kubectl commands with compact output |
| `rtk oc [cmd]` | OpenShift CLI (`oc`) commands with compact output |
| `rtk aws [cmd]` | AWS CLI with compact output (force JSON, compress) |

### Network

| Subcommand | Description |
|---|---|
| `rtk curl [args]` | Curl with auto-JSON detection and schema output |
| `rtk wget [args]` | Download with compact output (strips progress bars) |

### General-Purpose

| Subcommand | Description |
|---|---|
| `rtk test <cmd>` | Run tests and show only failures |
| `rtk err <cmd>` | Run command and show only errors/warnings |
| `rtk summary <cmd>` | Run command and show heuristic summary |
| `rtk smart <file>` | Generate 2-line technical summary of a file (heuristic-based) |
| `rtk json [args]` | Show JSON (compact values by default, or keys-only with `--keys-only`) |
| `rtk log [args]` | Filter and deduplicate log output |
| `rtk env [args]` | Show environment variables (filtered) |
| `rtk deps [args]` | Summarize project dependencies |
| `rtk pipe [args]` | Read stdin, apply filter, print filtered output (Unix pipe mode) |
| `rtk run [args]` | Execute argv directly, or a command string through an explicit shell |
| `rtk bypass [args]` | Execute command without filtering but track usage |
| `rtk recall [hash]` | Recall output a filter elided, by content hash |

### Analytics And Diagnostics

| Subcommand | Description |
|---|---|
| `rtk gain [flags]` | Show token savings summary and history |
| `rtk discover [flags]` | Discover missed RTK savings from agent session history |
| `rtk session [flags]` | Show RTK adoption across agent sessions |
| `rtk hook-audit` | Show hook rewrite audit metrics (requires `RTK_HOOK_AUDIT=1`) |
| `rtk cc-economics` | Claude Code economics: spending (ccusage) vs savings (rtk) analysis |

### Configuration And Pipeline

| Subcommand | Description |
|---|---|
| `rtk config [cmd]` | Show or modify configuration |
| `rtk rewrite [args]` | Rewrite a raw command to its RTK equivalent (single source of truth for hooks) |
| `rtk pipeline <cmd>` | Inspect, validate, and test the compression pipeline |
| `rtk methods` | List registered compression methods and their contracts |
| `rtk plugins <cmd>` | Author, list, and build your own pipeline methods (Rust plugins) |
| `rtk tasks` | List configured delegation tasks and their bindings |
| `rtk trust` | Trust project-local TOML filters in current directory |
| `rtk untrust` | Revoke trust for project-local TOML filters |
| `rtk verify` | Verify hook integrity and run TOML filter inline tests |

### Hook Integration

| Subcommand | Description |
|---|---|
| `rtk hook claude` | Process Claude Code PreToolUse hook (reads JSON from stdin) |
| `rtk hook antigravity` | Process Google Antigravity PreToolUse hook (reads JSON from stdin) |
| `rtk hook cursor` | Process Cursor Agent hook (reads JSON from stdin) |
| `rtk hook gemini` | Process Gemini CLI BeforeTool hook (reads JSON from stdin) |
| `rtk hook codex` | Process Codex CLI PreToolUse hook (reads JSON from stdin) |
| `rtk hook trae` | Process Trae PreToolUse hook (reads JSON from stdin) |
| `rtk hook copilot` | Process Copilot preToolUse hook (VS Code + Copilot CLI, reads JSON from stdin) |
| `rtk hook droid` | Process Factory Droid PreToolUse hook (reads JSON from stdin) |
| `rtk hook vibe` | Process Mistral Vibe CLI pre_tool hook (reads JSON from stdin) |
| `rtk hook opencode` | Answer for OpenCode's plugin |
| `rtk hook check` | Check how a command would be rewritten by the hook engine (dry-run) |

### LLM Proxy

| Subcommand | Description |
|---|---|
| `rtk llm-proxy setup` | Check the daemon is available and report which AI agents can be pointed at it |
| `rtk llm-proxy start` | Launch the proxy as a background daemon |
| `rtk llm-proxy stop` | Ask a running proxy to shut down |
| `rtk llm-proxy status` | Check whether the proxy is running and reachable |
| `rtk llm-proxy stats` | Print usage stats from a running proxy |
| `rtk llm-proxy config` | Get/set runtime settings on a running proxy |
| `rtk llm-proxy service` | Manage a per-user background service |

### Telemetry

| Subcommand | Description |
|---|---|
| `rtk telemetry` | Manage telemetry consent and data (RGPD/GDPR) |
| `rtk learn [flags]` | Learn CLI corrections from agent error history |

## Best Practices

- Always check `which rtk` before assuming RTK is available. Degrade gracefully by running native commands when RTK is not present.
- Use `rtk rewrite <command>` when you are unsure whether RTK has an equivalent. Exit code `1` means run the command unchanged.
- Use `rtk bypass <command>` only when a filtered output was genuinely unusable — not as a default.
- Run `rtk gain` after completing a task involving many commands if savings reporting is relevant to the conversation.
- Run `rtk discover` when you suspect commands ran outside RTK's hook during a session.
- Never re-run `rtk init` if the hooks are already active. Use `rtk verify` to confirm hook integrity.
