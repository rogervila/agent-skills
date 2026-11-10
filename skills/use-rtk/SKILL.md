---
name: use-rtk
description: Tells LLMs to use RTK (Rust Token Killer) when the rtk command is available, reducing LLM token consumption by 60-90% through transparent command output filtering, pipelines, delegation, and proxy optimization.
license: MIT
metadata:
  author: "Roger Vilà"
  repository: "https://github.com/rogervila/agent-skills"
  version: "1.2.0"
  keywords: "rtk, rust-token-killer, token-optimization, token-reduction, cli-proxy, llm-efficiency, command-output, filtering, pipeline, task-delegation, llm-proxy, git, cargo, pytest, phpunit, jest, vitest, docker, kubectl"
---

# Use RTK (Rust Token Killer)

When the `rtk` command is available in the environment, use it to wrap terminal commands and optimize token consumption. RTK is an agent-agnostic token optimization system that filters, summarizes, routes, and compresses what coding agents read and send. It cuts command output token volume by 60–90% while preserving every critical technical fact, error, diagnostic, and exit code.

## Activation Criteria

Activate this skill whenever:

- The `rtk` command is available in the environment (verify with `which rtk` or `rtk --version`).
- You are about to execute shell commands whose output could contain verbose logs, test suites, builds, diffs, file trees, or package installation progress.
- You are performing operations involving Git, testing, linting, building, searching files, inspecting dependencies, or viewing logs.
- You are reading large files (>350 lines) or heavy documentation where delegation to a worker model (`rtk bulk-read` / `rtk:delegate-reads`) avoids context bloat.
- You are working in an agent environment (such as Google Antigravity, Cline, or Kimi) where the host hook API does not transparently rewrite command inputs.

Do not use RTK for:

- Commands whose exact raw byte stream is the required artifact (e.g. tar archives, binary output, or output piped directly to destination files).
- Interactive terminal applications that require interactive TTY input.
- Shell constructs that cannot be parsed by RTK rewrites: subshell command substitutions (`$(...)`) and shell variable assignments. Run these native or use `rtk run -c "<cmd>"`.

## Decision Rule: Before Running Any Command

Before running any terminal command, follow this sequence:

1. **Check for a direct RTK subcommand**: If RTK has a specialized wrapper (e.g. `rtk git status`, `rtk cargo test`, `rtk pytest`, `rtk read <file>`), use it.
2. **If unsure**: Run `rtk rewrite "<command>"`:
   - Exit code `0`: Safe rewrite printed → use the printed RTK command.
   - Exit code `1`: No rewrite exists → execute the native command unchanged.
   - Exit code `2`: Deny rule matched → block execution.
   - Exit code `3`: Ask rule matched → ask user for confirmation before executing.
3. **If output is verbose but has no specialized command**: Use general wrappers:
   - Tests: `rtk test <command>`
   - Builds/commands: `rtk err <command>` or `rtk summary <command>`
   - Direct execution: `rtk run -c "<command>"`
   - Pipes: `<command> 2>&1 | rtk pipe -f <filter>`
4. **If output was unusable (empty/garbled/contradicting exit code)**: Re-run with `rtk bypass <command>`.
5. **If output was truncated and you need the elided section**: Recover using `rtk recall <hash>`.

## Core Command Mappings

Use these RTK subcommands in place of native tools:

### File System & Search

| Instead of | Use | Notes |
|---|---|---|
| `ls [path]` | `rtk ls [path]` | Accepts native `ls` flags (`-la`, `-lh`) |
| `ls -R [path]` | `rtk ls -R [path]` | Compact hierarchical listing |
| `tree [path]` | `rtk tree [path]` | Token-optimized tree structure |
| `cat <file>` | `rtk read <file>` | Intelligent structural preview |
| `find [args]` | `rtk find [args]` | Accepts `-name`, `-type`, `-maxdepth` |
| `grep [args]` | `rtk grep [args]` | Groups matches by file, truncates lines |
| `rg [args]` | `rtk rg [args]` | Runs ripgrep with compact grouping |
| `ast-grep [args]` | `rtk ast-grep [args]` | Structural AST search with grouping |
| `wc [args]` | `rtk wc [args]` | Strips redundant padding |
| `diff [args]` | `rtk diff [args]` | Changed lines only |

### Git & Version Control

| Instead of | Use | Notes |
|---|---|---|
| `git [subcommand]` | `rtk git [subcommand]` | `status`, `diff`, `log`, `add`, `commit`, `push` |
| `gh [subcommand]` | `rtk gh [subcommand]` | GitHub CLI PRs, issues, checks |
| `glab [subcommand]` | `rtk glab [subcommand]` | GitLab CLI |
| `gt [subcommand]` | `rtk gt [subcommand]` | Graphite stacked PRs |

### JavaScript / TypeScript / Node.js

| Instead of | Use | Notes |
|---|---|---|
| `npm run [script]` | `rtk npm [script]` | Strips lifecycle boilerplate |
| `npx [tool]` | `rtk npx [tool]` | Auto-routes `tsc`, `eslint`, `prisma` |
| `pnpm [cmd]` | `rtk pnpm [cmd]` | Ultra-compact package operations |
| `bun [cmd]` | `rtk bun [cmd]` | Bun runtime commands |
| `bunx [tool]` | `rtk bunx [tool]` | Passthrough with auto-filter |
| `tsc [args]` | `rtk tsc [args]` | Grouped error list by file |
| `eslint [args]` | `rtk lint [args]` | Grouped violations by rule |
| `prettier [args]` | `rtk prettier [args]` | Compact formatting checks |
| `jest [args]` | `rtk jest [args]` | Isolates test failures |
| `vitest [args]` | `rtk vitest [args]` | Isolates test failures |
| `playwright [args]` | `rtk playwright [args]` | Compact test failures |
| `next build` | `rtk next build` | Compact Next.js build stats |
| `ng build` / `ng test`| `rtk ng build` / `rtk ng test` | Compact Angular build/test tables |
| `prisma [cmd]` | `rtk prisma [cmd]` | Strips ASCII banners |
| `deno [cmd]` | `rtk deno [cmd]` | Deno runtime commands |

### Python

| Instead of | Use | Notes |
|---|---|---|
| `pytest [args]` | `rtk pytest [args]` | Isolates failures, trims tracebacks |
| `mypy [args]` | `rtk mypy [args]` | Grouped error output |
| `ruff check` / `format` | `rtk ruff check` / `format` | Compact linter/formatter output |
| `pip install [args]` | `rtk pip install [args]` | Strips wheel building and progress bars |
| `uv run [cmd]` | `rtk uv [cmd]` | Preserves uv virtual environment semantics |

### Rust

| Instead of | Use | Notes |
|---|---|---|
| `cargo test [args]` | `rtk cargo test [args]` | Failures only, passing collapsed to count |
| `cargo build [args]` | `rtk cargo build [args]` | Compact compilation diagnostics |
| `cargo clippy [args]` | `rtk cargo clippy [args]` | Compact clippy lint output |
| `cargo check [args]` | `rtk cargo check [args]` | Compact compiler check output |

### Go

| Instead of | Use | Notes |
|---|---|---|
| `go test [args]` | `rtk go test [args]` | Parses NDJSON, failures only |
| `go build [args]` | `rtk go build [args]` | Compact build output |
| `golangci-lint run` | `rtk golangci-lint run` | Grouped linter violations |

### PHP

| Instead of | Use | Notes |
|---|---|---|
| `php artisan [cmd]` | `rtk php artisan [cmd]` | Compact Laravel output |
| `./vendor/bin/phpunit`| `rtk phpunit [args]` | Test failures only |
| `./vendor/bin/phpstan`| `rtk phpstan [args]` | Grouped static analysis issues |
| `./vendor/bin/pest` | `rtk pest [args]` | Compact Pest test failures |
| `./vendor/bin/pint` | `rtk pint [args]` | Compact code style fixer output |

### Ruby / Rails

| Instead of | Use | Notes |
|---|---|---|
| `bundle exec rspec` | `rtk rspec [args]` | Shows only failing examples |
| `bundle exec rubocop`| `rtk rubocop [args]` | Grouped offense list |
| `rake test` | `rtk rake [args]` | Compact Minitest failures |

### Java / JVM / Scala / CTest

| Instead of | Use | Notes |
|---|---|---|
| `mvn [cmd]` / `./mvnw`| `rtk mvn [cmd]` | Compact Maven output |
| `mvnd [cmd]` | `rtk mvnd [cmd]` | Compact Maven Daemon output |
| `sbt [cmd]` | `rtk sbt [cmd]` | Compact SBT output |
| `./gradlew [cmd]` | `rtk gradlew [cmd]` | Android/Gradle wrapper output |
| `ctest [args]` | `rtk ctest [args]` | Compact CTest output |

### .NET

| Instead of | Use | Notes |
|---|---|---|
| `dotnet build/test` | `rtk dotnet build/test` | Compact build diagnostics and test failures |

### Infrastructure & Databases

| Instead of | Use | Notes |
|---|---|---|
| `docker [cmd]` | `rtk docker [cmd]` | Compact container list and deduplicated logs |
| `kubectl [cmd]` | `rtk kubectl [cmd]` | Strips extra whitespace and columns |
| `oc [cmd]` | `rtk oc [cmd]` | OpenShift CLI commands |
| `aws [cmd]` | `rtk aws [cmd]` | Forces JSON and removes metadata envelopes |
| `psql [args]` | `rtk psql [args]` | Strips table borders, compresses query results |
| `sqlfluff [args]` | `rtk sqlfluff [args]` | Compact SQL linter output |

### Network & Utilities

| Instead of | Use | Notes |
|---|---|---|
| `curl [args]` | `rtk curl [args]` | Auto-detects JSON, compacts schema |
| `wget [args]` | `rtk wget [args]` | Strips progress indicators |

## General-Purpose Wrappers & Pipe Mode

When a command has no dedicated RTK subcommand:

```bash
# Isolate test failures from any custom test command
rtk test ./scripts/run-all-tests.sh

# Run command and isolate errors and warnings
rtk err make all

# Run command and return a 2-line heuristic summary
rtk summary ./scripts/deploy.sh

# Inspect compact JSON structure (or keys only)
rtk json config.json
rtk json --keys-only config.json

# Execute arbitrary command string through explicit shell
rtk run -c "mvn clean && mvn test"

# Pipe output into a named filter
cargo test 2>&1 | rtk pipe -f cargo-test
pytest 2>&1 | rtk pipe -f pytest
find . -name "*.py" | rtk pipe -f find
```

## Pipelines and Task Delegation

RTK 1.x introduces a composable pipeline engine configured via `pipeline.toml`. Upgrading preserves the default compressor (`rtk:default`). Further optimizations can be adopted by extending reference pipelines:

```toml
# ~/.config/rtk/pipeline.toml
[pipeline]
extends = ["rtk:posthook", "rtk:proxy", "rtk:terse"]
```

### The Six Reference Pipelines

1. **`rtk:default`**: Baseline compressor. PreToolUse rewrite, proxy normalizer (`ansi`, `progress`, `dedup`), and awareness directive.
2. **`rtk:posthook`**: PostToolUse output compression for shell (`term`), file reads (`lockfile`), search (`matches`), and web (`web`).
3. **`rtk:proxy`**: Prompt-cache breakpoint alignment (`cache-align`) in the RTK Proxy daemon.
4. **`rtk:delegate-reads`**: Shunts file reads over 350 lines to a cheaper model (`bulk-read`), keeping the file body completely out of main context.
5. **`rtk:verbatim-diffs`**: Passes git diffs through byte-for-byte; enables line number stripping on reads.
6. **`rtk:terse`**: Injects directive `terse-output` instructing the agent to produce concise, fluff-free prose while keeping code and errors in full.

### Running Delegation Tasks

When tasks are configured with upstreams, agents can offload work directly from the CLI:

```bash
# Extract answers from large files without loading the file into context
rtk bulk-read --question "What are the configuration flags?" src/Config.java

# Run a heavy build and get a digested error summary
rtk check-build --question "Which modules failed and why?" -- mvn package

# Generate code against a reference template
rtk code-write --spec "Add user registration endpoint" --reference src/Auth.java --target src/Register.java
```

### Pipeline Management Commands

```bash
# Print resolved pipeline
rtk pipeline show

# Validate pipeline syntax and rules (exits non-zero on error)
rtk pipeline validate

# Trace why a command was compressed or rewritten
rtk pipeline explain --tool Bash --command "git log -20"

# Share a pipeline as a markdown card
rtk pipeline share --md

# Search community pipelines on GitHub
rtk pipeline search

# Adopt a community pipeline pinned to a git commit
rtk pipeline add github:owner/repo
```

## RTK Proxy and Launcher

The RTK Proxy daemon (`rtk-proxy`) optimizes provider-API traffic (conversation history, tool results, prompt-cache breakpoints):

```bash
# Launch Claude Code routed through rtk-proxy (starts daemon automatically)
rtk claude

# Check daemon health and agent compatibility
rtk llm-proxy setup
rtk llm-proxy status
rtk llm-proxy stats
```

## Output Recovery: Recall and Bypass

If RTK's filtered output is insufficient:

### 1. Hash Recall (`rtk recall`)

When RTK elides large output blocks, it prints a hash recovery hint (e.g. `[+80 lines elided: rtk recall a1b2c3d4]`). Retrieve the elided content without re-running the command:

```bash
# View elided lines
rtk recall a1b2c3d4

# View entire original output
rtk recall a1b2c3d4 --full

# Stream lines starting at line 50
rtk recall a1b2c3d4 --from 50 --lines 20
```

### 2. Unfiltered Bypass (`rtk bypass`)

Re-run the command without filtering while preserving usage tracking:

```bash
rtk bypass cargo test
rtk bypass git diff HEAD~1
```

> Use `rtk bypass` only when output was empty when output was clearly expected, contradicted the process exit code, or was garbled.

## Savings Analytics and Session Intelligence

```bash
# Global token savings dashboard
rtk gain

# View savings by layer (read, write, tool_result, history, cache)
rtk gain --by-layer

# View savings by compression method or rule
rtk gain --by-method
rtk gain --by-rule

# Compare Claude Code spending (ccusage) vs RTK savings
rtk cc-economics

# Find commands executed without RTK optimization
rtk discover

# Learn CLI error corrections and generate persistent rules
rtk learn --write-rules
```

## Agent Initialization (One-Time Setup)

To configure RTK hooks globally for your assistant environment:

```bash
# Google Antigravity
rtk init -g --agent antigravity

# Claude Code / Copilot
rtk init -g

# Cursor
rtk init -g --agent cursor

# Gemini CLI
rtk init -g --gemini

# Codex
rtk init -g --codex

# Windsurf / Devin Desktop
rtk init -g --agent windsurf

# Trae IDE
rtk init -g --agent trae

# Other agents: cline, kilocode, kimi, pi, omp, hermes, droid, vibe
rtk init -g --agent <agent-name>

# Verify hook integrity
rtk verify
```

## Quick Start Workflow

1. **Verify availability**: Run `which rtk` or `rtk --version`.
2. **Select command**: Look up the command in the Core Command Mappings above. If uncertain, check `rtk rewrite "<command>"`.
3. **Execute with RTK**: Use the RTK form (e.g. `rtk git status`, `rtk pytest`, `rtk read <file>`).
4. **Inspect & recover**: If lines were elided, retrieve them via `rtk recall <hash>`. If output was unusable, re-run with `rtk bypass <command>`.
5. **Check savings**: Run `rtk gain` after completing tasks to review token reduction impact.

## Non-Goals and Anti-patterns

- Do not use RTK for commands where raw binary or stream redirection is required (e.g. `tar -czf archive.tar.gz .`).
- Do not use RTK in automated production CI scripts where downstream tooling expects raw, non-compacted output schemas.
- Do not default to `rtk bypass`. Use it strictly when filtered output is empty, garbled, or contradictory.
- Do not re-run `rtk init` repeatedly if hooks are already active. Verify with `rtk verify`.

## Reference Documentation

- [RTK Overview And Usage](references/rtk-overview.md) — Problem statement, token savings economics, architecture and editions (`rtk`, `rtk-oss`, `rtk-proxy`), 20-agent coverage matrix, installation, and complete subcommand reference.
- [RTK Command Mappings](references/rtk-command-mappings.md) — Comprehensive command mapping tables across all languages and frameworks, general wrappers, pipe mode filters, `rtk read` flags, and verification.
- [RTK Pipelines and Delegation](references/rtk-pipelines.md) — Complete guide to `pipeline.toml`: the 6 reference pipelines (`rtk:default`, `rtk:posthook`, `rtk:proxy`, `rtk:delegate-reads`, `rtk:verbatim-diffs`, `rtk:terse`), task delegation (`bulk-read`, `code-write`), conditions, AI judges, methods, directives, and community pipeline sharing.
- [RTK Advanced Features](references/rtk-advanced-features.md) — RTK Proxy daemon and `rtk claude` launcher, token economics (`rtk gain`, `rtk cc-economics`), session intelligence (`rtk session`, `rtk discover`, `rtk learn`), bypass and hash recall recovery, hook architecture, and custom plugins.

## License

This skill is licensed under the [MIT License](../../LICENSE).
