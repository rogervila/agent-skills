---
name: "RTK Overview And Usage"
description: "What RTK (Rust Token Killer) is, how it works, editions, installation, agent initialization and coverage, subcommands, and best practices."
tags: [rtk, rust-token-killer, token-optimization, cli-proxy, editions, installation, initialization, agent-coverage, subcommands, llm-efficiency]
---

# RTK Overview And Usage

Last checked: 2026-11-10.

RTK (Rust Token Killer) is an agent-agnostic token optimization system that filters, summarizes, routes, and compresses what AI coding agents read and send. Originally created as a high-performance CLI compressor for terminal command output (reducing bash output by 60–90%), RTK 1.x expands into a composable token-optimization engine across shell commands, file reads, web fetches, sub-agent communication, and model API traffic.

Source repository: https://github.com/rtk-ai/rtk
Documentation: https://www.rtk-ai.app

## What Problem RTK Solves

AI coding agents read full command outputs, file contents, and tool results into their context window. Routine developer commands produce massive volumes of boilerplate output that bloat context and dilute reasoning:

- `git status` / `git diff` — dozens of lines with unchanged paths, mode lines, index headers, and redundant context.
- `cargo test` / `pytest` / `phpunit` / `jest` — hundreds of lines of passing test output when only failures matter.
- `ls -R` / `find` — deep recursive file listings with paths the LLM does not need.
- `npm install` / `pip install` — progress bars, spinners, and download summaries.
- Large file reads — entire 1,000+ line files loaded into context when only structural signatures or specific answers are needed.

RTK intercepts these streams and returns concise, signal-rich representations: errors, failures, file tree shapes, changed lines, and structured summaries. The agent gets all critical facts without token waste.

## How Token Savings Work

RTK reduces the **bash output, tool results, and API payloads** your agent reads. 

- **Bash output reduction**: RTK strips 60–90% of raw output bytes.
- **Context dilution**: Bash output is only one contributor to input tokens alongside the prompt, system instructions, and conversation history. Total bill reduction is therefore a subset of raw command savings.
- **Token estimation**: RTK reports estimated tokens as `bytes / 4`. Percentages are reliable metrics, while absolute token counts are close approximations.
- **Prompt cache safety**: RTK filters output once per command. Compact outputs are cached normally by provider prompt caches, reducing cache write and read costs.

## RTK Editions And Architecture

RTK ships in three distinct artifacts:

| Download | License | Contents |
|---|---|---|
| `rtk` (full edition) | Apache-2.0 + BUSL-1.1 | Hook core, all 100+ command filters, and the `rtk-engine` pipeline engine (evaluates `pipeline.toml`, tasks, judges, directives) |
| `rtk-oss` | Apache-2.0 only | Hook core and command filters only. Does not include the pipeline engine. |
| `rtk-proxy` | BUSL-1.1 | The standalone local HTTP daemon that intercepts and compresses provider-API traffic. Never bundled into `rtk`. |

> Production use of both `rtk` and `rtk-proxy` is free under the BUSL-1.1 Additional Use Grant. Commercial resale as a hosted product requires a commercial license.

Both `rtk` editions install a binary named `rtk`. They cannot be installed simultaneously; uninstall one before installing the other.

## Version

RTK version in this environment: **1.2.0**

Check installed version and health:

```bash
rtk --version   # Prints version (e.g. rtk 1.2.0)
rtk gain        # Displays savings dashboard
```

## Installation

> Install `rtk-ai/rtk`, not any unrelated crate named `rtk`.

### Package Managers

```bash
# macOS and Linux (Homebrew)
brew install rtk

# macOS and Linux (Apache-2.0 OSS edition)
brew install rtk-ai/tap/rtk-oss

# Windows (WinGet)
winget install rtk-ai.rtk
```

### Quick Install Script

```bash
# Full edition (default)
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh

# OSS edition
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | RTK_EDITION=oss sh
```

### Building From Source

```bash
cargo install --git https://github.com/rtk-ai/rtk --branch master rtk
```

## Agent Initialization

After installation, initialize RTK for your AI assistant environment. This configures the appropriate hook or awareness rule so commands are automatically routed through RTK.

```bash
# Claude Code / Copilot (default)
rtk init -g

# Google Antigravity
rtk init -g --agent antigravity

# Cursor
rtk init -g --agent cursor

# Gemini CLI
rtk init -g --gemini

# Codex (OpenAI)
rtk init -g --codex

# Windsurf / Devin Desktop
rtk init -g --agent windsurf

# Trae IDE
rtk init -g --agent trae

# Other supported agents
rtk init -g --agent cline       # Cline / Roo Code
rtk init -g --agent kilocode    # Kilo Code
rtk init -g --agent kimi        # Kimi AI
rtk init -g --agent pi          # Pi
rtk init -g --agent omp         # Oh My Pi (OMP)
rtk init -g --agent hermes      # Hermes
rtk init -g --agent droid       # Factory Droid
rtk init -g --agent vibe        # Mistral Vibe

# Preview changes without modifying files
rtk init --dry-run
rtk init --dry-run -v

# Verify hook integrity
rtk verify

# Uninstall hook configuration
rtk init --uninstall
```

## Agent Coverage Matrix

How much of a pipeline an agent can execute depends on what its hook API permits:

| Agent | Command Rewrite | Command Block | Compress Output | Add Context | Session Start | Route via Proxy |
|---|---|---|---|---|---|---|
| **Claude Code** | Yes | Yes | **Yes** | Yes | Yes | Yes (`rtk claude`) |
| **Copilot CLI** | Yes | Yes | **Yes** | Yes | Yes | Yes |
| **Hermes** | Yes | Yes | **Yes** | Yes | Yes | Yes |
| **Kilo Code** | Yes | Yes | **Yes** | Yes | — | Yes |
| **Mistral Vibe** | Yes | Yes | **Yes** | Yes | — | — |
| **Oh My Pi** | Yes | Yes | **Yes** | Yes | Yes | Yes |
| **OpenCode** | Yes | Yes | **Yes** | Yes | — | — |
| **Pi** | Yes | Yes | **Yes** | Yes | Yes | — |
| **Cursor** | Yes | Yes | MCP only | Yes | Yes | — |
| **Codex** | Yes | Yes | — | Yes | Yes | Yes |
| **Copilot (VS Code)** | Yes | Yes | — | Yes | Yes | — |
| **Factory Droid** | Yes | Yes | — | Yes | Yes | — |
| **Gemini CLI** | Yes | Yes | — | Yes | Yes | Yes |
| **OpenClaw** | Yes | Yes | — | — | Yes | Yes |
| **Trae** | Yes | Yes | — | Yes | Yes | — |
| **Windsurf / Devin** | Yes | Yes | — | Yes | Yes | — |
| **Antigravity** | — | Yes | — | — | — | — |
| **Cline** | — | Yes | — | Yes | — | Yes |
| **Kimi Code** | — | Yes | — | — | Yes | Yes |
| **Roo Code** | — | — | — | — | — | Yes |

> In environments like Google Antigravity, Cline, and Kimi Code where the host API does not permit mutating tool arguments or tool results in place, `rtk init` installs a rules file instructing the agent to invoke `rtk <command>` directly.

## Complete Subcommand Reference

All subcommands available in RTK 1.2.0:

### File System & Search

| Subcommand | Description |
|---|---|
| `rtk ls [paths...]` | List directory contents with token-optimized output (proxy to native `ls`) |
| `rtk tree [path]` | Directory tree with token-optimized output (proxy to native `tree`) |
| `rtk read <files...>` | Read file(s) with intelligent filtering (`--level`, `--max-lines`, `--head-lines`, `--tail-lines`, `--line-numbers`) |
| `rtk smart <file>` | Generate 2-line technical summary of a file (heuristic-based) |
| `rtk find [flags]` | Find files with compact tree output (accepts native `find` flags like `-name`, `-type`) |
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
| `rtk ng [cmd]` | Angular build with compact tables (`rtk ng build`, `rtk ng test`) |
| `rtk prisma [cmd]` | Prisma commands with compact output (no ASCII art) |
| `rtk playwright [args]` | Playwright E2E tests with compact output |
| `rtk deno [cmd]` | Deno runtime commands with compact output |

### Python

| Subcommand | Description |
|---|---|
| `rtk pytest [args]` | Pytest test runner with compact output |
| `rtk mypy [args]` | Mypy type checker with grouped error output |
| `rtk ruff [args]` | Ruff linter/formatter with compact output (`check`, `format`) |
| `rtk pip [args]` | Pip package manager with compact output (auto-detects uv) |
| `rtk uv [cmd]` | uv run with compact output while preserving uv-managed environment semantics |

### Rust

| Subcommand | Description |
|---|---|
| `rtk cargo [subcommand]` | Cargo commands with compact output (`test`, `build`, `clippy`, `check`) |

### Go

| Subcommand | Description |
|---|---|
| `rtk go [cmd]` | Go commands with compact output (`test`, `build`) |
| `rtk golangci-lint [cmd]` | golangci-lint wrapper with compact `run` support |

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

### Java / JVM / Scala / CTest

| Subcommand | Description |
|---|---|
| `rtk mvn [cmd]` | Apache Maven wrapper with compact output |
| `rtk mvnd [cmd]` | Maven Daemon (mvnd) with compact output |
| `rtk sbt [cmd]` | SBT (Scala Build Tool) commands with compact output |
| `rtk gradlew [cmd]` | Android Gradle wrapper with compact output |
| `rtk ctest [args]` | CTest with compact output |

### .NET

| Subcommand | Description |
|---|---|
| `rtk dotnet [cmd]` | .NET commands with compact output (`build`, `test`, `restore`, `format`) |

### Databases & SQL

| Subcommand | Description |
|---|---|
| `rtk psql [args]` | PostgreSQL client with compact output (strip borders, compress tables) |
| `rtk sqlfluff [args]` | SQLFluff SQL linter with compact output (`lint`, `fix`) |

### Infrastructure & Cloud

| Subcommand | Description |
|---|---|
| `rtk docker [cmd]` | Docker commands with compact output |
| `rtk kubectl [cmd]` | Kubectl commands with compact output |
| `rtk oc [cmd]` | OpenShift CLI (`oc`) commands with compact output |
| `rtk aws [cmd]` | AWS CLI with compact output (force JSON, compress) |

### Network & Web

| Subcommand | Description |
|---|---|
| `rtk curl [args]` | Curl with auto-JSON detection and schema output |
| `rtk wget [args]` | Download with compact output (strips progress bars) |

### General-Purpose Execution & Pipe Mode

| Subcommand | Description |
|---|---|
| `rtk test <cmd>` | Run tests and show only failures |
| `rtk err <cmd>` | Run command and show only errors/warnings |
| `rtk summary <cmd>` | Run command and show heuristic summary |
| `rtk json [args]` | Show JSON (compact values by default, or keys-only with `--keys-only`) |
| `rtk log [args]` | Filter and deduplicate log output |
| `rtk env [args]` | Show environment variables (filtered) |
| `rtk deps [args]` | Summarize project dependencies |
| `rtk pipe [args]` | Read stdin, apply named filter, print filtered output (Unix pipe mode) |
| `rtk run [args]` | Execute argv directly, or a command string through an explicit shell (`-c`) |
| `rtk bypass [args]` | Execute command without filtering but track usage |
| `rtk recall [hash]` | Recall output a filter elided, by content hash |

### Pipeline Engine & Methods

| Subcommand | Description |
|---|---|
| `rtk pipeline <cmd>` | Inspect, validate, test, benchmark, share, and evaluate compression pipelines |
| `rtk methods [cmd]` | List registered compression methods (`rtk methods list`) and their contracts |
| `rtk tasks [cmd]` | List configured delegation tasks (`rtk tasks list`) and upstream bindings |
| `rtk plugins <cmd>` | Author, list, and build your own pipeline methods in Rust (`new`, `list`, `build`) |
| `rtk trust` | Trust project-local TOML filters and pipelines in current directory |
| `rtk untrust` | Revoke trust for project-local TOML filters and pipelines |
| `rtk verify` | Verify hook integrity and run filter inline tests |

### Analytics & Diagnostics

| Subcommand | Description |
|---|---|
| `rtk gain [flags]` | Show token savings summary, graphs, and attribution history |
| `rtk discover [flags]` | Discover missed RTK savings opportunities from session history |
| `rtk session [flags]` | Show RTK adoption across coding assistant sessions |
| `rtk cc-economics [flags]`| Claude Code economics: spending (ccusage) vs savings (rtk) analysis |
| `rtk learn [flags]` | Learn CLI corrections from assistant error history and generate rules |
| `rtk hook-audit` | Show hook rewrite audit metrics (requires `RTK_HOOK_AUDIT=1`) |

### LLM Proxy & Launchers

| Subcommand | Description |
|---|---|
| `rtk claude` | Launch Claude Code routed through `rtk-proxy` (starts daemon automatically) |
| `rtk llm-proxy setup` | Check proxy daemon availability and compatible agents |
| `rtk llm-proxy start` | Launch the proxy as a background daemon |
| `rtk llm-proxy stop` | Stop the running proxy daemon |
| `rtk llm-proxy status` | Check proxy health and reachability |
| `rtk llm-proxy stats` | Print real-time proxy traffic and savings stats |
| `rtk llm-proxy config` | Get or set runtime proxy settings |
| `rtk llm-proxy service` | Manage proxy background service |

### Hooks & Internal

| Subcommand | Description |
|---|---|
| `rtk rewrite <cmd>` | Check command rewrite without running it (single source of truth for hooks) |
| `rtk hook <agent>` | Process agent hook payload from stdin (`claude`, `antigravity`, `cursor`, etc.) |
| `rtk hook check` | Dry-run check for hook rewrite engine |
| `rtk telemetry [cmd]` | Manage GDPR telemetry consent and settings |
| `rtk config [cmd]` | View or modify global RTK configuration |

## Best Practices

- Check availability first with `which rtk` or `rtk --version`.
- Wrap shell commands with the appropriate `rtk <subcommand>` when working in environments without transparent argument rewriting (e.g. Antigravity, Cline).
- Query `rtk rewrite <command>` when uncertain whether RTK provides a specialized filter. If exit code is `1`, run the native command unchanged.
- Reserve `rtk bypass <command>` strictly for instances where filtered output was empty, garbled, or contradicted the process exit code.
- Leverage `rtk recall <hash>` using hashes printed in RTK truncation notices to recover specific elided output without re-executing.
- Use `rtk pipeline show` and `rtk pipeline validate` when configuring or modifying `pipeline.toml`.
- Run `rtk gain` periodically or at task completion to measure token reduction impact.
