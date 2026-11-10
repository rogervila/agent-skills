---
name: "RTK Pipelines and Delegation"
description: "Architecture and reference for RTK pipeline.toml, the 6 reference pipelines, task delegation, conditions, AI judges, methods, directives, and sharing."
tags: [rtk, pipeline, pipeline-toml, task-delegation, reference-pipelines, conditions, classifiers, judges, directives, methods, plugins, sharing]
---

# RTK Pipelines and Delegation

Introduced in RTK 1.x, the RTK Engine is a declarative pipeline system governed by `pipeline.toml`. Instead of hardcoding what commands get rewritten and how outputs are compressed, the engine defines *where* RTK acts, *when* it fires, and *what* transforms or delegations it executes.

With no pipeline file present, RTK defaults to `rtk:default` (the standard bash compressor, awareness file, and `filters.toml`). Everything beyond that is opt-in.

## Architecture and File Hierarchy

### Where Pipelines Live

| Scope | Location | Notes |
|---|---|---|
| Built-in | `rtk:default`, `rtk:posthook`, `rtk:proxy`, `rtk:delegate-reads`, `rtk:verbatim-diffs`, `rtk:terse` | Compiled into `rtk` binary |
| User | `~/.config/rtk/pipeline.toml` | User-wide configuration (loads first) |
| User directory | `~/.config/rtk/pipelines/*.toml` | Loaded alphabetically (`10-*.toml`, `20-*.toml`) |
| Project | `.rtk/pipeline.toml` | Project-scoped, **trust-gated** via `rtk trust` |
| Project directory | `.rtk/pipelines/*.toml` | Each file is individually trust-gated |
| Custom filters | `~/.config/rtk/filters.toml`, `.rtk/filters.toml` | Custom regex/string command filters (trust-gated) |
| Runtime status | `~/.local/share/rtk/pipeline-status.json` | Recorded pipeline load issues |
| Decision log | `~/.local/share/rtk/pipeline.log` | Opt-in decision log |

On macOS, the user directory is `~/Library/Application Support/rtk/`. On Windows, it is `%APPDATA%\rtk\`.

### Load Order and Precedence

1. Built-in reference pipelines named in `extends`.
2. User `~/.config/rtk/pipeline.toml`.
3. User `~/.config/rtk/pipelines/*.toml` (alphabetical).
4. Project `.rtk/pipeline.toml` (if trusted).
5. Project `.rtk/pipelines/*.toml` (if trusted).

Later definitions override earlier ones. Within one rule list, project rules evaluate before user rules, which evaluate before inherited built-in rules. First matching rule wins unless `continue = true`.

### Fail-Open vs Fail-Closed Semantics

- **Transform rules fail open**: If a compression rule names an unknown method or condition, RTK emits a warning (`W014`/`W015`), skips that specific rule, and keeps the rest of the pipeline active.
- **Control rules fail closed**: If a rule with an action (`deny`, `route`, `rewrite`, `passthrough`) has an error or unknown task kind, the entire pipeline file fails to load. Safety and routing rules never degrade silently.

## Layout of `pipeline.toml`

```toml
schema_version = 1

[pipeline]
name = "my-pipeline"
extends = ["rtk:posthook", "rtk:proxy"]
enabled = true

# Hook rules (inside agent tool lifecycle)
[[hook.before_tool.shell]]
name   = "rtk-rewrite"
action = "rewrite"

[[hook.before_tool.read]]
name   = "shunt-large-read"
when   = { file_lines_gt = 350, whole_file = true }
action = "route"
task   = "bulk-read"

[[hook.after_tool.shell]]
name = "term-default"
when = { is_rtk_command = false }
use  = ["term"]

# Proxy rules (daemon HTTP traffic)
[[proxy.request.tool_result]]
name = "normalize"
use  = ["ansi", "progress", "dedup"]

[[proxy.request.cache]]
name = "align"
use  = ["cache-align"]

# Agent directives
[[directive]]
use = "terse-output"

# Model upstreams and delegation tasks
[upstream.flash]
provider    = "google"
model       = "gemini-2.5-flash"
api_key_env = "GEMINI_API_KEY"

[task.bulk-read]
kind     = "summarize"
upstream = "flash"

# Overrides for inherited rules
[override.shunt-large-read]
when.file_lines_gt = 500

[guards]
never_worse = true
min_size    = 512
```

## The Six Reference Pipelines

RTK ships six built-in reference pipelines that can be extended or inspected with `rtk pipeline show <name>`:

### 1. `rtk:default`
The baseline compressor. Applies `PreToolUse` rewrite on `shell` commands, normalizes `tool_result` via `ansi`, `progress`, and `dedup` in proxy mode, and injects the `rtk-awareness` directive.

```toml
schema_version = 1
[pipeline]
name = "rtk:default"

[[hook.before_tool.shell]]
name   = "rtk-rewrite"
action = "rewrite"

[[proxy.request.tool_result]]
name = "normalize"
use  = ["ansi", "progress", "dedup"]

[[directive]]
use   = "rtk-awareness"
level = "default"

[guards]
never_worse = true
min_size = 512
```

### 2. `rtk:posthook`
Compresses output across all tool types in `PostToolUse`: shell output with `term`, dependency lockfiles with `lockfile`, search output with `matches` (grep-group), and web responses with `web`.

```toml
[pipeline]
name = "rtk:posthook"
extends = "rtk:default"

[[hook.after_tool.shell]]
name = "term-default"
when = { is_rtk_command = false }
use  = ["term"]

[[hook.after_tool.read]]
name = "lockfiles"
when = { basename_in = ["package-lock.json", "Cargo.lock", "yarn.lock", "pnpm-lock.yaml"] }
use  = ["lockfile"]

[[hook.after_tool.search]]
name = "grep-group"
when = { format = "matches" }
use  = ["matches"]

[[hook.after_tool.web]]
name = "web-default"
use  = ["web"]
```

### 3. `rtk:proxy`
Enables prompt cache alignment in the RTK Proxy daemon via `cache-align` on `proxy.request.cache`. Works with Anthropic-dialect traffic.

```toml
[pipeline]
name = "rtk:proxy"
extends = "rtk:default"

[[proxy.request.cache]]
name = "align"
use  = ["cache-align"]
```

### 4. `rtk:delegate-reads`
Delegates whole-file reads over 350 lines to a cheaper model. The file never enters the agent's main context.

```toml
[pipeline]
name = "rtk:delegate-reads"
extends = "rtk:default"

[task.bulk-read]
kind = "summarize"

[task.code-write]
kind = "generate"

[[hook.before_tool.read]]
name   = "shunt-large-read"
when   = { file_lines_gt = 350, whole_file = true }
action = "route"
task   = "bulk-read"
```

### 5. `rtk:verbatim-diffs`
Keeps git diffs and show outputs byte-for-byte identical while enabling line number stripping on reads for agents that address edits without line numbers.

```toml
[pipeline]
name = "rtk:verbatim-diffs"
extends = ["rtk:posthook", "rtk:proxy"]

[override.strip-line-numbers]
enabled = true

[[hook.before_tool.shell]]
name   = "keep-diffs"
when   = { command_matches = "^git (diff|show)\\b" }
action = "passthrough"
```

### 6. `rtk:terse`
Directs the agent to produce concise, terse responses without conversational filler, while leaving code, paths, commands, and errors complete.

```toml
[pipeline]
name = "rtk:terse"
extends = "rtk:default"

[[directive]]
use = "terse-output"
```

## The Rule Tree

A rule's position in the TOML table defines its site, event, and subject:

```
[[<site>.<event>.<subject>]]
```

| Segment | Meaning | Values |
|---|---|---|
| **site** | Interception mechanism | `hook` (agent hook) · `proxy` (daemon API traffic) |
| **event** | When the rule executes | `before_tool` · `after_tool` · `request` |
| **subject** | Tool category or request part | Hook: `shell`, `read`, `write`, `edit`, `search`, `web`, `subagent`, `mcp`, `any`<br>Proxy: `tool_result`, `tool_use`, `assistant`, `cache`, `any` |

### Rule Actions and Keys

| Action | Allowed Positions | Description |
|---|---|---|
| `rewrite` | `hook.before_tool.shell` | Prefixes command with `rtk` if a specialized filter exists |
| `deny` | `hook.before_tool.*` | Refuses tool call with a custom `message` |
| `passthrough` | Any hook or proxy position | Halts rule evaluation and passes content through unfiltered |
| `route` | `hook.before_tool.*`, `hook.after_tool.*` | Hands work over to a delegation task bound to an upstream model |

### Route Modes Before a Tool

When routing before a tool runs, `mode` dictates how the delegation executes:

| Mode | Behavior | Extra Turn? | Supported Subjects |
|---|---|---|---|
| `suggest` *(default)* | Denies call and instructs agent to invoke `rtk <task> ...` | Yes | All subjects, all agents |
| `swap` | In-place replaces command with `rtk <task> --question "..." -- <cmd>` | No | `shell` |
| `answer` | RTK executes task synchronously and returns worker's answer to agent | No | `read`, `search`, `web` |

## Task Delegation System

Tasks allow coding agents to offload heavy reading, command digestion, and boilerplate generation to smaller, faster, cheaper models (e.g. Gemini 2.5 Flash, Claude 3.5 Haiku).

### Task Kinds

| Kind | Purpose | Agent CLI Syntax |
|---|---|---|
| `summarize` | File reading + targeted question | `rtk <task> --question "..." <paths...>` |
| `digest` | Command execution / output capture + question | `rtk <task> --question "..." -- <command>` |
| `generate` | Specification + reference file → target output | `rtk <task> --spec "..." --reference <ref> --target <target>` |

### Upstreams Configuration

An upstream defines the model provider and endpoint:

```toml
[upstream.flash]
provider     = "google"               # anthropic, openai, google, or custom
model        = "gemini-2.5-flash"
api_key_env  = "GEMINI_API_KEY"       # Environment variable holding the key
timeout_secs = 20                     # Timeout in seconds (default 30)
```

> **Credential Borrowing**: When the RTK Proxy daemon is running, tasks whose upstreams match the agent's provider (`anthropic`, `openai`) automatically borrow the agent's relayed credential if no separate API key is specified in the environment.

### Call Context Integration

Setting `context = true` on a task passes the agent's current transcript context to the worker model:
- The user's active goal/prompt
- The agent's current step description
- The last 5 tool calls

## Conditions and AI Judges

Rules use `when` tables to filter when they fire. Keys support operator suffixes:

| Suffix | Meaning | Example |
|---|---|---|
| *(none)* | Exact equality | `format = "json"`, `whole_file = true` |
| `_in`, `_not_in` | Array membership | `basename_in = ["Cargo.lock", "package-lock.json"]` |
| `_starts_with` | String prefix | `command_starts_with = "git "` |
| `_matches` | Regular expression | `command_matches = "^git (diff\|show)\\b"` |
| `_gt`, `_gte`, `_lt`, `_lte` | Numerical comparison | `file_lines_gt = 350`, `tokens_gt = 2000` |

### Context Keys

- **File**: `file_path`, `extension`, `basename`, `whole_file`, `file_lines`, `file_bytes`, `file_exists`
- **Command**: `command`, `command_starts_with`, `command_matches`, `is_rtk_command`, `exit_code`
- **Output**: `format` (`term`, `json`, `web`, `matches`, `lockfile`), `bytes`, `lines`, `tokens`, `duration_ms`
- **Call Context**: `intent` (agent reasoning), `goal` (user prompt), `recent_calls` (last tool calls)

### AI Classifiers (Judges)

A `[classifier.<name>]` evaluates semantic conditions using a fast System One judge model:

```toml
[upstream.judge]
provider     = "google"
model        = "gemini-2.5-flash"
api_key_env  = "GEMINI_API_KEY"
timeout_secs = 5

[classifier.skim]
upstream     = "judge"
question     = "noul"                 # choice, score, or noul (boolean)
instructions = "Is a concise summary sufficient for the agent's goal?"
input_chars  = 1500

[[hook.before_tool.read]]
name   = "judge-large-reads"
when   = { file_lines_gt = 300, whole_file = true, "noul.skim_gte" = 0.8 }
action = "route"
task   = "bulk-read"
```

Judges always **fail open**: if an endpoint times out or fails, the fact is absent and the call passes through untouched. Judges cannot be applied to `deny` actions.

## Methods, Chains, and Plugins

Methods are individual text transformations applied in `use = [...]` arrays.

### Registered Methods

- **Lossless (Hook + Proxy)**: `ansi` (strip escape codes), `dedup` (collapse identical lines), `web-md` (HTML to markdown).
- **Lossy with Recall**: `progress` (keep last animation frame), `cap` (keep head 50 + tail 200 lines if >300 lines), `toon` (table-of-objects notation), `minify-json`, `grep-group` (group by file), `rle`, `shape`, `truncate`.
- **Lossy without Recall**: `base64-elide` (replace large base64 blobs), `lockfile` (package@version list), `md-slim` (strip badges/comments), `strip-line-numbers`.
- **Proxy-Resident**: `cache-align` (place Anthropic prompt cache breakpoint), `ccr` (content-addressed context reduction), `retire-pointer` (replace written file bodies with disk pointers).

### Shipped Composite Chains

| Chain | Included Methods |
|---|---|
| `term` | `["ansi", "progress", "dedup", "base64-elide", "cap"]` |
| `json` | `["base64-elide", "toon"]` |
| `web` | `["ansi", "base64-elide", "web-md", "toon", "md-slim"]` |
| `matches` | `["grep-group"]` |

### Authoring Custom Chains & Rust Plugins

```toml
# In pipeline.toml:
[method.gentle]
chain = ["ansi", "dedup"]
```

For custom native transforms, RTK provides a Rust plugin scaffolding CLI:

```bash
rtk plugins new my-plugin     # Scaffold plugin crate in ~/.config/rtk/plugins/
rtk plugins list              # List active and scaffolded plugins
rtk plugins build             # Build and link custom rtk binary
```

## Directives

Directives place structured instructions in the agent's context every turn:

- `rtk-awareness`: Instructs the agent on RTK awareness levels (`default`, `high`, `full`).
- `terse-output`: Instructs the agent to provide terse, high-density responses.
- `route-tasks`: Automatically generated whenever tasks have configured upstreams.

## Pipeline CLI Commands

| Command | Purpose |
|---|---|
| `rtk pipeline show [name]` | Print resolved pipeline (or a named built-in like `rtk:default`) |
| `rtk pipeline validate` | Validate pipeline syntax and rules; exits non-zero on errors |
| `rtk pipeline test` | Parse, resolve, and validate every loaded pipeline file |
| `rtk pipeline status` | Print last recorded load failure or silent fallback details |
| `rtk pipeline explain [flags]` | Trace which rules fire for a hypothetical input (`--tool`, `--command`, `--file`, `--last`) |
| `rtk pipeline bench <file>` | Benchmark token compression on a local text file |
| `rtk pipeline share [--md]` | Render share card (terminal format or markdown) |
| `rtk pipeline share publish` | Publish pipeline to GitHub repository or Gist with secret scanning |
| `rtk pipeline add <source>` | Install community pipeline (e.g. `github:owner/repo`, `card.md`, `--shadow`) |
| `rtk pipeline search [query]` | Search GitHub for `rtk-pipeline` tagged repositories |
| `rtk pipeline eval <name>` | Shadow-evaluate candidate pipeline on live sessions without modifying output |
| `rtk pipeline promote <name>` | Promote shadow install to live (or `--discard`) |
| `rtk pipeline log [on\|off\|tail]`| Toggle or inspect the decision log |

## Best Practices

- Always run `rtk pipeline validate` after editing `pipeline.toml`.
- When testing new compression rules, test safely using `shadow = true` or `rtk pipeline add <source> --shadow`.
- When delegating whole-file reads with `rtk:delegate-reads`, ensure an upstream is configured with an active API key.
- Never place API keys directly in `pipeline.toml`; always use `api_key_env` or `api_key_command`.
- Keep `timeout_secs` on upstreams low (5–10s) when rules sit on synchronous hook paths.
- Re-run `rtk init -g` whenever you add rules covering new tool categories (e.g. adding `hook.after_tool.*` rules requires registering the `PostToolUse` hook).
