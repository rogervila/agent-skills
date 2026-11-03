---
name: "RTK Advanced Features"
description: "RTK pipeline system, LLM proxy, plugin authoring, token analytics commands, bypass and recall recovery, and rewrite hook integration."
tags: [rtk, pipeline, llm-proxy, plugins, token-analytics, bypass, recall, rewrite, hooks, gain, discover, session, telemetry, config, learn]
---

# RTK Advanced Features

This reference covers RTK features beyond basic command substitution: the pipeline system, LLM proxy, plugin authoring, analytics, bypass/recall recovery, and hook integration details.

## The RTK Compression Pipeline

RTK's output filtering is implemented as a configurable pipeline of rules. Each rule applies a compression method to matching command output.

### Inspecting The Pipeline

```bash
# Show the resolved pipeline
rtk pipeline show

# Show a specific built-in literal
rtk pipeline show rtk:default
rtk pipeline show rtk:posthook

# Validate all pipeline files (exits non-zero on errors)
rtk pipeline validate

# Explain what fires for a given agent/tool/format and why
rtk pipeline explain

# Check every loaded pipeline file: parse, resolve, validate
rtk pipeline test

# Run the resolved chain over a local file and report before/after tokens
rtk pipeline bench <file>

# Show the last recorded pipeline load problem
rtk pipeline status
```

### Pipeline Sharing And Discovery

RTK pipelines can be shared and adopted from the community:

```bash
# Share a pipeline (terminal card, or markdown when piped)
rtk pipeline share
rtk pipeline share --md

# Find shared pipelines on GitHub (topic: rtk-pipeline)
rtk pipeline search

# Adopt a shared pipeline (validate, install, report requirements)
rtk pipeline add <pipeline>

# Shadow-evaluate an installed pipeline on live sessions (non-destructive)
rtk pipeline eval <pipeline>

# Promote a shadow-installed pipeline to live, or discard it
rtk pipeline promote <pipeline>
rtk pipeline promote --discard <pipeline>

# View the opt-in decision log
rtk pipeline log
```

### Pipeline Methods

```bash
# List registered compression methods and their contracts
rtk methods

# Author, list, and build your own pipeline methods (Rust plugins)
rtk plugins list
rtk plugins build
```

### Custom TOML Filters

Projects can ship their own TOML filter rules. RTK requires explicit trust before using local filters.

```bash
# Trust project-local TOML filters in current directory
rtk trust

# Revoke trust for project-local TOML filters
rtk untrust

# Verify hook integrity and run TOML filter inline tests
rtk verify
```

## LLM Proxy

The LLM proxy is a separate RTK component that intercepts LLM API requests and compresses input tokens at the prompt level — not just command output. It operates transparently alongside the hook-based output filtering.

```bash
# Check proxy daemon availability and agent compatibility
rtk llm-proxy setup

# Start the proxy as a background daemon
rtk llm-proxy start

# Check proxy running status
rtk llm-proxy status

# Print proxy usage stats
rtk llm-proxy stats

# Get or set runtime settings on a running proxy
rtk llm-proxy config

# Manage a per-user background service
rtk llm-proxy service

# Stop the proxy
rtk llm-proxy stop
```

When the LLM proxy is running, `rtk gain` automatically launches a live full-screen dashboard (`--watch` mode). Use `--text` to force the static view instead.

## Token Analytics

### Savings Summary

```bash
# Global token savings
rtk gain

# Current project only
rtk gain --project

# ASCII graph of daily savings
rtk gain --graph

# Recent command history
rtk gain --history

# Monthly quota savings estimate
rtk gain --quota

# Detailed daily breakdown
rtk gain --daily

# Weekly breakdown
rtk gain --weekly

# Monthly breakdown
rtk gain --monthly

# All time breakdowns (daily + weekly + monthly)
rtk gain --all

# Live full-screen dashboard
rtk gain --watch

# Force static text view even when llm-proxy is running
rtk gain --text
```

### Savings Attribution

```bash
# Per compression method
rtk gain --by-method

# Per pipeline rule
rtk gain --by-rule

# By token layer (read, tool_result, history, ...)
rtk gain --by-layer

# Per pipeline
rtk gain --by-pipeline

# One pipeline's savings, sliced by where they land
rtk gain --pipeline <name>

# What shadow rules would have saved (recorded, never emitted)
rtk gain --shadow
```

### Output Formats

```bash
# Text (default)
rtk gain --format text

# JSON
rtk gain --format json

# CSV
rtk gain --format csv
```

### Recall Efficiency

```bash
# Show recall efficiency per filter (elisions vs agent recalls)
rtk gain --recalls

# Show parse failure log (commands that fell back to raw execution)
rtk gain --failures
```

### Resetting Stats

```bash
# Reset token savings and recall stats to zero
rtk gain --reset

# Skip confirmation prompt
rtk gain --reset --yes
```

### Claude Code Economics

```bash
# Compare Claude Code spending (ccusage) vs RTK savings
rtk cc-economics
```

## Session And Discovery Analytics

```bash
# Show RTK adoption across Claude Code sessions
rtk session

# Discover commands from the past 30 days that missed RTK optimization
rtk discover

# Filter by current project
rtk discover --project .

# Scan all projects
rtk discover --all

# Limit to last N days
rtk discover --since 7

# Limit results per section
rtk discover --limit 10

# JSON output
rtk discover --format json
```

## Hook Integration

RTK provides hook processors for all major AI coding agents. These allow RTK to transparently rewrite commands before they run, without the agent needing to know about RTK.

### Hook Processor Commands

```bash
# Process a hook (reads JSON from stdin, writes rewrite to stdout)
rtk hook claude        # Claude Code PreToolUse
rtk hook antigravity   # Google Antigravity PreToolUse
rtk hook cursor        # Cursor Agent
rtk hook gemini        # Gemini CLI BeforeTool
rtk hook codex         # Codex CLI PreToolUse
rtk hook trae          # Trae PreToolUse
rtk hook copilot       # VS Code + Copilot CLI preToolUse
rtk hook droid         # Factory Droid PreToolUse
rtk hook vibe          # Mistral Vibe CLI pre_tool
rtk hook opencode      # OpenCode plugin response

# Dry-run: check how a command would be rewritten
rtk hook check
```

### `rtk rewrite` Exit Codes

`rtk rewrite <command>` is the single source of truth for hook rewrites.

| Exit code | Meaning | Hook action |
|---|---|---|
| `0` | Rewrite printed; allow rules cover every command | Hook may auto-allow |
| `1` | No rewrite available | Run the command unchanged |
| `2` | A deny rule matched | Block the command |
| `3` | Rewrite printed; ask rule matched or allow rules don't cover all commands | Use the rewrite, defer approval to host |

```bash
rtk rewrite "git status"
# prints: rtk git status
# exit 0

rtk rewrite "some-unknown-tool"
# no output
# exit 1

rtk rewrite "rm -rf /"
# no output (deny)
# exit 2
```

### Hook Audit

```bash
# Show hook rewrite audit metrics (requires RTK_HOOK_AUDIT=1)
RTK_HOOK_AUDIT=1 rtk hook-audit
```

## Bypass And Recall Recovery

### Bypass

`rtk bypass` executes a command without filtering but still tracks usage. Use it only when a filtered output was genuinely unusable (empty when output was expected, contradicting exit code, or garbled).

```bash
rtk bypass cargo test
rtk bypass git diff HEAD~1
```

> `rtk proxy` is a deprecated alias for `rtk bypass` — both work identically. Prefer `rtk bypass` in new instructions.

### Recall

When RTK filters output, it can store elided content for later recall using a content hash shown in the recovery hint.

```bash
# Recall elided content by hash (a unique prefix is enough)
rtk recall abc123

# Recall full output, not just the missed part
rtk recall abc123 --full

# Start from line N of the full output
rtk recall abc123 --from 50

# Return only first N lines
rtk recall abc123 --lines 20

# Filter recalled lines by regex
rtk recall abc123 --grep "ERROR"

# List all stored entries
rtk recall --list
```

### Recall Mode Configuration

```bash
# Show or set recovery mode: sqlite | tee | disabled
rtk config recall
rtk config recall sqlite
rtk config recall disabled
```

## Pipe Mode (Unix Pipe)

RTK can filter stdin from any command in Unix pipe mode:

```bash
# Named filter
cargo test 2>&1 | rtk pipe -f cargo-test
pytest 2>&1 | rtk pipe -f pytest
cat large-log.txt | rtk pipe -f git-log

# Passthrough (no filtering, useful for debugging)
some-command | rtk pipe --passthrough
```

Available named filters: `cargo-test`, `pytest`, `phpunit`, `phpstan`, `pint`, `grep`, `find`, `git-log`.

## Learning From History

RTK can scan agent error history to identify CLI corrections worth persisting as rules:

```bash
# Scan current project sessions from last 30 days
rtk learn

# Scan all projects
rtk learn --all

# Limit to last N days
rtk learn --since 7

# Set minimum confidence threshold (0.0–1.0)
rtk learn --min-confidence 0.8

# Set minimum occurrence count to include in report
rtk learn --min-occurrences 2

# Generate .claude/rules/cli-corrections.md
rtk learn --write-rules

# JSON output
rtk learn --format json
```

## Configuration

```bash
# Show current config
rtk config

# Create default config file
rtk config --create

# Show or set recall mode
rtk config recall
rtk config recall sqlite
rtk config recall tee
rtk config recall disabled
```

## Telemetry

```bash
# Manage telemetry consent and data (RGPD/GDPR)
rtk telemetry
```

## Task Delegation

```bash
# List configured delegation tasks and their bindings
rtk tasks
```

## Verbosity

RTK supports three verbosity levels, recognized before the subcommand:

```bash
rtk -v <subcommand>     # Verbose
rtk -vv <subcommand>    # More verbose
rtk -vvv <subcommand>   # Most verbose
```

## Environment Variables

| Variable | Effect |
|---|---|
| `RTK_HOOK_AUDIT=1` | Enable hook rewrite audit metrics (used with `rtk hook-audit`) |
| `SKIP_ENV_VALIDATION=1` | Skip environment variable validation for child processes (Next.js, tsc, lint, prisma) — can also be passed as `--skip-env` flag |
| `RTK_REWRITE_HOST=openclaw` | For a delegate that gates commands itself — turns exit 3 into exit 0 |

## Smart File Summary

```bash
# Generate a 2-line technical summary of a file (heuristic model)
rtk smart <file>
```

## JSON Inspection

```bash
# Compact JSON values (default)
rtk json <file>

# Keys-only output
rtk json --keys-only <file>
```

## Best Practices

- Use the pipeline system to share project-specific compression rules with the team via `rtk pipeline share` and `rtk pipeline add`.
- Enable the LLM proxy with `rtk llm-proxy start` for additional input-token savings on top of output filtering.
- Run `rtk discover` after onboarding a new project to identify commands that are running outside RTK's hook coverage.
- Use `rtk learn --write-rules` to capture CLI corrections from past sessions as persistent rules.
- Check `rtk gain --by-method` to understand which compression methods contribute most savings in your workflow.
- Keep recall mode set to `sqlite` (default) so that elided content can always be recovered with `rtk recall`.
- Audit hooks periodically with `rtk verify` to confirm hook integrity after agent or RTK updates.
