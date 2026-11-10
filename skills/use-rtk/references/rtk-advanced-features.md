---
name: "RTK Advanced Features"
description: "RTK Proxy daemon, token analytics and economics, session intelligence, bypass and recall recovery, hook integration details, and custom plugins."
tags: [rtk, llm-proxy, rtk-proxy, token-analytics, gain, cc-economics, session, discover, learn, bypass, recall, hooks, plugins, config]
---

# RTK Advanced Features

This guide details RTK's advanced operational capabilities beyond standard command wrapping: the RTK Proxy daemon, token economics analytics, session intelligence, hash-based recall recovery, hook architecture, and custom plugins.

## RTK Proxy (`rtk-proxy`)

The RTK Proxy daemon extends token optimization from terminal outputs to the provider-API requests your agent sends. Operating as a local background daemon, it intercepts conversation history, tool results, file bodies, and cache directives before forwarding requests to model endpoints.

```
Claude Code ──▶ rtk-proxy ──▶ api.anthropic.com
                   │
                   ├─ normalize: strip ANSI / progress redraws / duplicate lines
                   ├─ execute proxy.request rules from pipeline.toml
                   ├─ place prompt-cache breakpoints (cache-align)
                   └─ record usage ──▶ rtk gain
```

### Installation and Binaries

The daemon binary is named `rtk-proxy`. It is distributed as a standalone archive (`rtk-proxy-<target>`) licensed under BUSL-1.1 and is not bundled inside the `rtk` archive.

Place `rtk-proxy` in the same directory as `rtk` or anywhere on your system `$PATH`.

From source:
```bash
cargo build --release --manifest-path proxy/Cargo.toml
```

### The `rtk claude` Launcher

For zero-configuration execution without modifying settings:

```bash
rtk claude
```

`rtk claude` checks if `rtk-proxy` is running (spawning it automatically if needed), sets `ANTHROPIC_BASE_URL` to the daemon's loopback endpoint, and replaces its process with `claude` using native `exec`. All signals, stdio, and exit codes remain intact.

### Daemon Management Commands

Manage the daemon directly via `rtk llm-proxy`:

```bash
# Verify daemon binary and list compatible agents
rtk llm-proxy setup

# Launch proxy daemon in the background
rtk llm-proxy start

# Check running status and port connectivity
rtk llm-proxy status

# View live traffic and compression statistics
rtk llm-proxy stats

# Stop the proxy daemon
rtk llm-proxy stop

# Inspect or adjust runtime configuration
rtk llm-proxy config

# Manage persistent per-user background service
rtk llm-proxy service install
rtk llm-proxy service start
rtk llm-proxy service status
```

### Binding to Custom Ports

By default, the daemon binds to `127.0.0.1:8080`. Custom bindings can be configured with `--bind`:

```bash
rtk llm-proxy start --bind 127.0.0.1:9090
rtk llm-proxy status --bind 127.0.0.1:9090
```

### Proxy Compression Capabilities

1. **Normalization**: Strips ANSI escape codes, terminal redraw sequences, and duplicate lines from tool results in conversation history.
2. **Cache Alignment (`cache-align`)**: Places Anthropic prompt-cache breakpoints to maximize cache hits on turn prefixes.
3. **Content-Addressed Context Reduction (CCR)**: Replaces large historical tool results in old conversation turns with compact retrieval tokens while preserving exact originals in `~/.config/rtk/llm-proxy/rtk-proxy-memory.db` for expansion if referenced.
4. **Credential Borrowing**: Tasks routed through the proxy automatically reuse the agent's active API credential.

## Token Analytics and Economics

RTK measures exact character and byte reductions, converting them into estimated token metrics (`bytes / 4`).

### `rtk gain` Dashboard

```bash
# Global token savings summary
rtk gain

# Scope to current project only
rtk gain --project

# ASCII graph of daily savings (last 30 days)
rtk gain --graph

# Recent command history with before/after token counts
rtk gain --history

# Day-by-day savings breakdown
rtk gain --daily

# Weekly breakdown
rtk gain --weekly

# Monthly breakdown
rtk gain --monthly

# Comprehensive report (daily + weekly + monthly)
rtk gain --all

# Live dashboard mode (default when rtk-proxy is running)
rtk gain --watch

# Force static text rendering
rtk gain --text
```

### Attribution Reporting

Inspect exactly which parts of your setup contribute savings:

```bash
# Sliced by token layer (read, write, tool_result, history, cache)
rtk gain --by-layer

# Sliced by individual pipeline rule
rtk gain --by-rule

# Sliced by compression method (term, ansi, dedup, lockfile, etc.)
rtk gain --by-method

# Sliced by active pipeline
rtk gain --by-pipeline

# View what shadow-mode rules would have saved
rtk gain --shadow

# Show recall efficiency (elisions vs agent recall requests)
rtk gain --recalls

# View parse failure fallback log
rtk gain --failures
```

### Export Formats

```bash
rtk gain --format text    # Default text format
rtk gain --format json    # Machine-readable JSON export
rtk gain --format csv     # CSV spreadsheet export
```

### Claude Code Economics (`rtk cc-economics`)

Analyzes net financial savings by cross-referencing actual provider spending data (`ccusage`) with token reductions achieved by RTK:

```bash
# Spending vs savings analysis
rtk cc-economics

# Breakdowns
rtk cc-economics --daily
rtk cc-economics --weekly
rtk cc-economics --monthly
rtk cc-economics --all
rtk cc-economics --format json
```

## Session Intelligence and Learning

### Session Adoption Tracking (`rtk session`)

Inspects how consistently RTK was utilized across coding assistant sessions:

```bash
rtk session
```

### Discovering Missed Savings (`rtk discover`)

Scans transcript history to locate commands that were executed without RTK wrapping:

```bash
# Scan current project (past 30 days)
rtk discover

# Scan all local projects
rtk discover --all

# Limit scan to past N days
rtk discover --since 7

# Limit results per category
rtk discover --limit 10

# Export as JSON
rtk discover --format json
```

### Automated Rule Learning (`rtk learn`)

Scans agent error and retry history across sessions to discover repetitive mistakes and generate project-specific rules:

```bash
# Scan error patterns in current project
rtk learn

# Scan across all projects
rtk learn --all

# Filter by confidence threshold (0.0 - 1.0)
rtk learn --min-confidence 0.8

# Require minimum occurrence count
rtk learn --min-occurrences 2

# Write learned corrections directly into assistant rules file
rtk learn --write-rules
```

## Bypass and Content Recall

### Unfiltered Execution (`rtk bypass`)

When an RTK output filter produces malformed results, use `rtk bypass` to run the native binary directly without output manipulation. Usage remains tracked in `rtk gain` with 0% reduction:

```bash
# Raw execution of tests
rtk bypass cargo test

# Raw git log
rtk bypass git log -n 50
```

> **Criteria for Bypass**: Use `rtk bypass` only when output was empty when output was clearly expected, contradicted the process exit code, or was garbled.

### Elision Recovery (`rtk recall`)

When RTK truncates large outputs, it stores the elided content in a local database and prints a recovery hint with a content hash. Recover elided text without re-executing:

```bash
# Recall elided portion by hash prefix
rtk recall 3f8a1b2c

# Recall the entire original stream
rtk recall 3f8a1b2c --full

# Retrieve lines starting at offset 100
rtk recall 3f8a1b2c --from 100 --lines 50

# Search through stored output
rtk recall 3f8a1b2c --grep "FATAL"

# List all stored recall entries
rtk recall --list
```

### Recall Mode Configuration

Configure how RTK stores elisions in `~/.config/rtk/config.toml`:

```bash
rtk config recall sqlite    # Local SQLite store (default, supports full query flags)
rtk config recall tee       # Temporary file tee
rtk config recall disabled  # Disable recall storage
```

## Hook Integration Architecture

RTK processes hook events from AI coding tools through dedicated hook processors:

```bash
rtk hook claude        # Claude Code PreToolUse
rtk hook antigravity   # Google Antigravity PreToolUse
rtk hook cursor        # Cursor Agent hook
rtk hook gemini        # Gemini CLI BeforeTool
rtk hook codex         # Codex CLI PreToolUse
rtk hook trae          # Trae PreToolUse
rtk hook copilot       # Copilot preToolUse
rtk hook droid         # Factory Droid PreToolUse
rtk hook vibe          # Mistral Vibe CLI pre_tool
rtk hook opencode      # OpenCode plugin
rtk hook check         # Dry-run test of hook engine
```

### Single Source of Truth: `rtk rewrite`

The `rtk rewrite` command determines whether and how a command should be transformed before execution. Hook integrations evaluate this command and inspect its exit code:

| Exit Code | Meaning | Action |
|---|---|---|
| `0` | Rewrite printed; covered by allow rules | Transparently execute rewritten command |
| `1` | No rewrite available | Execute original command unchanged |
| `2` | Deny rule matched | Block execution |
| `3` | Rewrite printed but ask rule matched | Defer confirmation to user before execution |

Example:
```bash
rtk rewrite "git status"
# Outputs: rtk git status
# Exit code: 0
```

### Hook Auditing

Audit hook rewrite activity by setting `RTK_HOOK_AUDIT=1`:

```bash
RTK_HOOK_AUDIT=1 rtk hook-audit --since 7
```

### Hook Verification

Verify hook configuration and rule health:

```bash
rtk verify
```

## Custom Filters and Rust Plugins

### Custom TOML Command Filters

Custom command filters live in `~/.config/rtk/filters.toml` or project-local `.rtk/filters.toml`:

```toml
schema_version = 1

[filters.custom-build]
description          = "Custom internal build script"
match_command        = "^build-internal\\b"
strip_ansi           = true
strip_lines_matching = ["^\\[DEBUG\\]", "^Downloading dependencies"]
max_lines            = 150
on_empty             = "(build succeeded with no warnings)"

[[tests.custom-build]]
name     = "removes debug lines"
input    = "[DEBUG] connecting...\nBuild complete."
expected = "Build complete."
```

Project-local filter files must be explicitly trusted:

```bash
# Trust project-local filters
rtk trust

# Revoke trust
rtk untrust
```

### Rust Native Plugins

Custom compression methods or task kinds can be authored in native Rust:

```bash
# Scaffold new plugin crate in ~/.config/rtk/plugins/
rtk plugins new my-transform

# List active and scaffolded plugins
rtk plugins list

# Compile custom rtk binary with plugins linked in
rtk plugins build
```

## Environment Variables

| Variable | Effect |
|---|---|
| `RTK_HOOK_AUDIT=1` | Activates hook rewrite audit logging |
| `SKIP_ENV_VALIDATION=1` | Skips child process environment checks (`--skip-env`) |
| `RTK_PROXY_BIND` | Default address for `rtk-proxy` (e.g. `127.0.0.1:9090`) |
| `RTK_PROXY_RELAY_BORROWING=false` | Disables proxy credential borrowing for worker tasks |
| `RTK_REWRITE_HOST=openclaw` | Treats exit code 3 as 0 for hosts that manage permissions |

## Best Practices

- Use `rtk claude` to launch Claude Code with automatic proxy routing and cache alignment.
- Run `rtk gain --by-layer` to assess which token streams (reads, writes, or tool results) consume the most context in your projects.
- Run `rtk discover` when onboarding existing repositories to find frequently executed commands missing optimization.
- Use `rtk learn --write-rules` to turn repetitive command errors into persistent guardrail rules.
- Rely on `rtk recall <hash>` before resorting to `rtk bypass` when debugging truncated test output.
- Keep `rtk config recall` set to `sqlite` to retain recovery guarantees.
