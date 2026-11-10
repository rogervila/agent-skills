---
name: "RTK Command Mappings"
description: "Complete mapping of native terminal commands to their RTK equivalents, organized by ecosystem, with flags, wrappers, and usage notes."
tags: [rtk, command-mapping, git, cargo, pytest, jest, vitest, phpunit, docker, kubectl, npm, pnpm, bun, tsc, eslint, prettier, mypy, ruff, go, ruby, java, maven, dotnet, grep, find, ls]
---

# RTK Command Mappings

Use these tables to look up the correct RTK subcommand before running any command in the terminal. When working with an agent that does not transparently rewrite command inputs (such as Google Antigravity or Cline), always prefix commands with `rtk <subcommand>`.

If a command is not listed below, check `rtk rewrite "<command>"` to confirm if a specialized rewrite exists, or wrap it using `rtk test`, `rtk err`, `rtk summary`, or `rtk run`.

## Decision Flow

1. **Direct mapping exists**: Run `rtk <subcommand> [args]`.
2. **Unsure**: Run `rtk rewrite "<command>"`.
   - Exit 0: Safe rewrite printed, use it.
   - Exit 1: No rewrite available, run native command unchanged.
   - Exit 2: Deny rule matched, block command.
   - Exit 3: Rewrite printed but requires approval, defer to user.
3. **No direct mapping, but output is verbose**: Use general wrappers (`rtk test`, `rtk err`, `rtk summary`, or `rtk run -c "<cmd>"`).
4. **Output was unusable (empty/garbled/contradictory)**: Re-run with `rtk bypass <command>`.
5. **Elided output needed**: Recover with `rtk recall <hash>`.

## File System & Content Inspection

| Native command | RTK command | Notes |
|---|---|---|
| `ls [path]` | `rtk ls [path]` | Accepts native `ls` flags (`-la`, `-lh`) |
| `ls -R [path]` | `rtk ls -R [path]` | Compact hierarchical tree |
| `tree [path]` | `rtk tree [path]` | Token-optimized tree format |
| `cat <file>` | `rtk read <file>` | Intelligent structural filtering |
| `cat <f1> <f2>` | `rtk read <f1> <f2>` | Concatenates with per-file headers |
| `find [flags]` | `rtk find [flags]` | Accepts standard `find` flags (`-name`, `-type`, `-maxdepth`) |
| `grep [flags]` | `rtk grep [flags]` | Strips whitespace, truncates, groups by file |
| `rg [flags]` | `rtk rg [flags]` | Runs ripgrep natively with compact grouping |
| `ast-grep [flags]` | `rtk ast-grep [flags]` | Runs ast-grep with grouped match outputs |
| `wc [flags]` | `rtk wc [flags]` | Strips redundant paths and padding |
| `diff [args]` | `rtk diff [args]` | Ultra-condensed diff showing only changed lines |
| *(summary inspection)* | `rtk smart <file>` | Generates a 2-line heuristic technical summary |
| `cat <json-file>` | `rtk json <file>` | Compact JSON structure (or `rtk json --keys-only <file>`) |

### `rtk read` Flags

`rtk read` intelligently inspects files without dumping raw lines blindly into context:

| Flag | Description |
|---|---|
| `--level none` | Output raw content without structural filtering (default) |
| `--level minimal` | Light filtering (removes comment blocks, excessive blanks) |
| `--level aggressive` | Heavy filtering for large files (retains signatures, definitions, interfaces) |
| `--max-lines N` | Structural preview capped at N lines (retains imports, signatures; not arbitrary truncation) |
| `--head-lines N` | Retain only the first N lines |
| `--tail-lines N` | Retain only the last N lines |
| `--line-numbers` | Show line-number prefixes |

## Git & Version Control

| Native command | RTK command | Notes |
|---|---|---|
| `git status` | `rtk git status` | Grouped by state with concise counts |
| `git diff [args]` | `rtk git diff [args]` | Strips index headers and redundant context |
| `git log [args]` | `rtk git log [args]` | Hash, author, date, and commit subject |
| `git add [args]` | `rtk git add [args]` | Single-line confirmation |
| `git commit [args]` | `rtk git commit [args]` | Clean summary without verbose hook outputs |
| `git push [args]` | `rtk git push [args]` | Strips remote progress counters |
| `git [subcommand]` | `rtk git [subcommand]` | All git subcommands pass through RTK |
| `gh [subcommand]` | `rtk gh [subcommand]` | GitHub CLI (pull requests, issues, releases) |
| `glab [subcommand]` | `rtk glab [subcommand]` | GitLab CLI |
| `gt [subcommand]` | `rtk gt [subcommand]` | Graphite stacked PR management |

## JavaScript / TypeScript / Node.js

| Native command | RTK command | Notes |
|---|---|---|
| `npm run <script>` | `rtk npm <script>` | Strips npm banner and lifecycle boilerplate |
| `npm test` | `rtk npm test` | Retains test failures only |
| `npx tsc [args]` | `rtk npx tsc [args]` | Auto-routed to specialized tsc filter |
| `npx eslint [args]` | `rtk npx eslint [args]` | Auto-routed to specialized lint filter |
| `npx prisma [cmd]` | `rtk npx prisma [cmd]` | Auto-routed to prisma filter |
| `npx [tool]` | `rtk npx [tool]` | Intelligent routing based on executable |
| `pnpm [cmd]` | `rtk pnpm [cmd]` | Ultra-compact package operations |
| `yarn [cmd]` | `rtk npm [cmd]` or `rtk pnpm [cmd]` | Use tool matching package manager |
| `bun [cmd]` | `rtk bun [cmd]` | Bun runtime and package manager |
| `bunx [tool]` | `rtk bunx [tool]` | Bunx passthrough with auto-filter |
| `tsc [args]` | `rtk tsc [args]` | Grouped error output by file and code |
| `eslint [args]` | `rtk lint [args]` | Grouped violations by rule and file |
| `prettier [args]` | `rtk prettier [args]` | Compact formatting checks |
| `prettier/black/ruff` | `rtk format [args]` | Universal formatting checker |
| `jest [args]` | `rtk jest [args]` | Displays test failures only |
| `vitest [args]` | `rtk vitest [args]` | Displays test failures only |
| `playwright [args]` | `rtk playwright [args]` | Compact E2E results and failed assertions |
| `next build` | `rtk next build` | Compact Next.js build stats |
| `ng build` | `rtk ng build` | Compact Angular build tables with diagnostics |
| `ng test` | `rtk ng test` | Compact Angular test runner output |
| `prisma [cmd]` | `rtk prisma [cmd]` | Strips ASCII banners and redundant migration text |
| `deno [cmd]` | `rtk deno [cmd]` | Deno runtime commands |

## Python

| Native command | RTK command | Notes |
|---|---|---|
| `pytest [args]` | `rtk pytest [args]` | Shows only failures and trimmed tracebacks |
| `python -m pytest [args]` | `rtk pytest [args]` | Identical to direct pytest |
| `mypy [args]` | `rtk mypy [args]` | Grouped error output by file and type code |
| `ruff check [args]` | `rtk ruff check [args]` | Grouped rule violations |
| `ruff format [args]` | `rtk ruff format [args]` | Formatter diagnostics |
| `pip install [args]` | `rtk pip install [args]` | Strips progress bars and build wheels |
| `pip [args]` | `rtk pip [args]` | Auto-detects uv if available |
| `uv run [cmd]` | `rtk uv [cmd]` | Compact output preserving uv environment |

## Rust

| Native command | RTK command | Notes |
|---|---|---|
| `cargo test [args]` | `rtk cargo test [args]` | Collapses passing tests to counts, shows failures |
| `cargo build [args]` | `rtk cargo build [args]` | Strips compilation lines, shows diagnostics |
| `cargo check [args]` | `rtk cargo check [args]` | Grouped compiler warnings and errors |
| `cargo clippy [args]` | `rtk cargo clippy [args]` | Compact clippy lint output |
| `cargo [any]` | `rtk cargo [any]` | All cargo subcommands |

## Go

| Native command | RTK command | Notes |
|---|---|---|
| `go test [args]` | `rtk go test [args]` | Parses NDJSON, outputs failures only |
| `go build [args]` | `rtk go build [args]` | Compact build output |
| `golangci-lint run` | `rtk golangci-lint run` | Grouped linter violations |
| `golangci-lint [cmd]` | `rtk golangci-lint [cmd]` | Passes through for non-run subcommands |

## PHP

| Native command | RTK command | Notes |
|---|---|---|
| `php artisan [cmd]` | `rtk php artisan [cmd]` | Compact Laravel artisan output |
| `php -l [file]` | `rtk php -l [file]` | Compact syntax check output |
| `./vendor/bin/phpunit` | `rtk phpunit [args]` | Shows only test failures and assertion errors |
| `./vendor/bin/phpstan analyse`| `rtk phpstan [args]` | Grouped static analysis issues |
| `./vendor/bin/pest [args]` | `rtk pest [args]` | Compact Pest test failures |
| `./vendor/bin/paratest` | `rtk paratest [args]` | Compact parallel test output |
| `./vendor/bin/ecs check` | `rtk ecs check [args]` | Compact EasyCodingStandard output |
| `./vendor/bin/pint [args]` | `rtk pint [args]` | Compact Laravel Pint / PHP-CS-Fixer output |
| `php run-tests.php [args]` | `rtk phpt [args]` | Compact .phpt summary and failure diffs |

## Ruby / Rails

| Native command | RTK command | Notes |
|---|---|---|
| `bundle exec rspec` | `rtk rspec [args]` | Shows only failing examples and tracebacks |
| `bundle exec rubocop` | `rtk rubocop [args]` | Grouped offense list by file and cop |
| `rake test` | `rtk rake [args]` | Compact Minitest failures |

## Java / JVM / Scala / CTest

| Native command | RTK command | Notes |
|---|---|---|
| `mvn [cmd]` / `./mvnw` | `rtk mvn [cmd]` | Maven wrapper with build/test compression |
| `mvnd [cmd]` | `rtk mvnd [cmd]` | Maven Daemon with identical filters |
| `sbt [cmd]` | `rtk sbt [cmd]` | Scala Build Tool compact build/test output |
| `./gradlew build` | `rtk gradlew build` | Compact Gradle build output |
| `./gradlew test` | `rtk gradlew test` | Shows failing Gradle test classes |
| `./gradlew lint` | `rtk gradlew lint` | Android/Java linting diagnostics |
| `ctest [args]` | `rtk ctest [args]` | Compact CTest output |

## .NET

| Native command | RTK command | Notes |
|---|---|---|
| `dotnet build [args]` | `rtk dotnet build [args]` | Compact compiler warnings and errors |
| `dotnet test [args]` | `rtk dotnet test [args]` | Shows failed unit tests only |
| `dotnet restore [args]` | `rtk dotnet restore [args]`| Strips package download spam |
| `dotnet format [args]` | `rtk dotnet format [args]` | Compact format status |

## Infrastructure & Cloud

| Native command | RTK command | Notes |
|---|---|---|
| `docker ps` | `rtk docker ps` | Essential container fields only |
| `docker logs [args]` | `rtk docker logs [args]` | Deduplicated log lines with timestamps |
| `docker build [args]` | `rtk docker build [args]`| Strips progress steps, displays errors |
| `kubectl get [args]` | `rtk kubectl get [args]` | Strips extra whitespace and columns |
| `kubectl logs [args]` | `rtk kubectl logs [args]`| Filtered and deduplicated pod logs |
| `oc [cmd]` | `rtk oc [cmd]` | OpenShift CLI commands |
| `aws [cmd]` | `rtk aws [cmd]` | Forces JSON mode, removes metadata envelopes |

## Databases & SQL

| Native command | RTK command | Notes |
|---|---|---|
| `psql [args]` | `rtk psql [args]` | Strips table borders, compresses query results |
| `sqlfluff lint [args]` | `rtk sqlfluff lint [args]`| Grouped SQL lint violations |
| `sqlfluff fix [args]` | `rtk sqlfluff fix [args]` | Summary of fixed rules |

## Network

| Native command | RTK command | Notes |
|---|---|---|
| `curl [args]` | `rtk curl [args]` | Auto-detects JSON, compacts schema |
| `wget [args]` | `rtk wget [args]` | Strips progress indicators |

## General-Purpose Wrappers

When a specific command does not have a dedicated subcommand in RTK, wrap it with one of the following general-purpose utilities:

| Wrapper | Purpose | Example |
|---|---|---|
| `rtk test <cmd...>` | Run any custom test suite and isolate failures | `rtk test ./scripts/custom-runner.sh` |
| `rtk err <cmd...>` | Filter any command to display only errors and warnings | `rtk err make all` |
| `rtk summary <cmd...>` | Run any command and return a heuristic summary | `rtk summary ./deploy.sh` |
| `rtk run [args...]` | Run arbitrary executable directly without shell parsing | `rtk run mybinary --flag` |
| `rtk run -c "<cmd>"` | Run command string through explicit shell (`sh`/`cmd`) | `rtk run -c "mvn clean && mvn test"` |
| `rtk pipe -f <filter>` | Read stdin and apply a named filter | `cat app.log \| rtk pipe -f git-log` |

### Named Filters for Pipe Mode (`rtk pipe`)

Pipe standard output and error through `rtk pipe -f <filter>`:

```bash
cargo test 2>&1 | rtk pipe -f cargo-test
pytest 2>&1 | rtk pipe -f pytest
phpunit 2>&1 | rtk pipe -f phpunit
phpstan 2>&1 | rtk pipe -f phpstan
pint 2>&1 | rtk pipe -f pint
grep -rn "pattern" . | rtk pipe -f grep
find . -name "*.rs" | rtk pipe -f find
git log -n 50 | rtk pipe -f git-log
```

## Task Delegation Commands

When configured in `pipeline.toml`, agents can run specialized delegation tasks that hand work to smaller, cheaper worker models:

| Command | Kind | Usage |
|---|---|---|
| `rtk <task> --question "..." <paths...>` | `summarize` | Extracts specific facts from large files without loading the file into context |
| `rtk <task> --question "..." -- <command>` | `digest` | Runs command and digests verbose output into key facts |
| `rtk <task> --spec "..." --reference <ref> --target <target>` | `generate` | Generates a new file from a specification and reference template |

Example:

```bash
# Read a 3,000-line service file without loading it into main context:
rtk bulk-read --question "What are the authentication endpoints and their parameters?" src/Service.java

# Run a heavy build and get a digested failure report:
rtk check-build --question "Which modules failed compilation and what are the exact compiler errors?" -- mvn package
```

## Bypass and Output Recovery

RTK filters output to minimize token consumption. When an output is suspect or incomplete:

### 1. Bypass Filtering (`rtk bypass`)

Execute the exact native command without filtering, while continuing to track usage analytics:

```bash
# Full git log without truncation
rtk bypass git log -n 30

# Full test output with passing tests
rtk bypass cargo test

# Raw curl output
rtk bypass curl -s https://api.example.com/health
```

> Use `rtk bypass` only when the filtered output was unusable: empty when output was expected, contradicting the process exit code, or garbled.

### 2. Hash Recall (`rtk recall`)

When RTK elides large output blocks, it prints a recovery hint with a content hash (e.g. `[+120 lines elided: rtk recall a1b2c3d4]`). Retrieve the original elided text without re-running the command:

```bash
# Recall elided lines by hash prefix
rtk recall a1b2c3d4

# Recall the entire original output (not just elided section)
rtk recall a1b2c3d4 --full

# Stream lines starting at offset N
rtk recall a1b2c3d4 --from 40 --lines 20

# Grep through the recalled output
rtk recall a1b2c3d4 --grep "NullPointerException"

# List all stored recall entries
rtk recall --list
```

## Checking Rewrites Before Execution

Before running an unfamiliar command, check how RTK treats it:

```bash
rtk rewrite "git status"
# Outputs: rtk git status
# Exit code: 0 (safe rewrite)

rtk rewrite "custom-internal-script"
# No output
# Exit code: 1 (run unchanged)
```

## Best Practices

- Prefer `rtk read` over `cat` for viewing source files and configuration.
- Use `rtk grep` or `rtk rg` over native `grep` or `rg` for searching codebases.
- Do not use RTK with commands where exact raw byte streams are required for file output redirection (e.g. `tar -czf`, binary output, or piping directly into files).
- When a test suite fails unexpectedly with unclear output, inspect the elided text with `rtk recall <hash>` before resorting to `rtk bypass`.
