---
name: performance-optimization
description: Guides agents to improve performance with measured bottleneck analysis, efficient algorithms, lower allocations, better I/O patterns, and benchmark-backed validation.
license: MIT
metadata:
  author: "Roger Vilà"
  repository: "https://github.com/rogervila/agent-skills"
  version: "1.0.1"
  keywords: "performance, optimization, efficiency, benchmarking, profiling, algorithms, complexity, big-o, memory, allocations, concurrency, parallelization, throughput, latency, hot-path, scalability"
---

# Performance Optimization

Use this skill when performance is an explicit goal or an obvious risk: latency, throughput, memory, CPU, startup time, build time, I/O, database load, concurrency, or scalability. The objective is to make code faster or lighter without changing observable behavior, and to verify improvements with measurements whenever measurement is feasible.

Performance is a first-class design constraint, but correctness, security, and maintainability still set the boundaries. Prefer efficient choices when they are equally clear. Reserve invasive rewrites, clever micro-optimizations, and added complexity for measured hot paths or high-risk workloads.

## Activation Criteria

Use this skill when the task includes:

- Explicit performance terms such as optimize, speed up, slow, bottleneck, latency, throughput, memory, allocation, CPU, hot path, scalability, benchmark, profile, N+1, cache, or concurrency.
- Code that runs frequently, handles large data, sits in request/build/render loops, or performs repeated I/O or database work.
- Review of an implementation where algorithmic complexity, excessive allocations, blocking I/O, unbounded concurrency, or resource leaks are likely to cause real cost.
- Choosing between otherwise similar implementations where one is clearly more efficient with no meaningful readability or correctness penalty.

Do not use this skill as the primary lens when:

- The user asks only for formatting, naming, documentation, product copy, or style cleanup.
- The code is one-off setup, migration, test fixture generation, or administrative scripting and no performance concern is stated.
- A change would trade away correctness, security, accessibility, compatibility, or clear repository conventions for speculative speed.
- The repository already has a failing functional bug and no evidence that performance is the root cause.

## Required Inputs And Prerequisites

Before optimizing, gather as much of this context as the task allows:

- The performance goal or symptom: target latency, throughput, memory ceiling, CPU limit, timeout, build duration, or user-visible slowdown.
- The workload shape: input sizes, call frequency, data distribution, concurrency level, environment, and whether the path is CPU-bound or I/O-bound.
- A baseline: profiler output, benchmark results, logs, query plans, traces, flamegraphs, reproduction steps, or a small benchmark you can run locally.
- Correctness requirements and existing tests that must continue passing.
- Repository constraints: language/runtime version, framework conventions, supported platforms, dependencies, and deployment limits.

If no baseline exists, create a focused measurement when practical. If measurement is impossible, state the assumption and choose low-risk changes that are justified by complexity analysis or clearly redundant work.

## Optimization Workflow

1. **Define the metric.** Name what should improve and what must not regress.
2. **Find the hot path.** Use profiling, tracing, query plans, logs, or code inspection tied to workload frequency.
3. **Preserve behavior.** Run or add focused correctness tests before changing risky logic.
4. **Choose the highest-leverage fix.** Prefer algorithmic improvements, batching, fewer allocations, streaming, indexes, caching, or bounded concurrency over cosmetic micro-tuning.
5. **Keep the change narrow.** Optimize the bottleneck without broad rewrites or unrelated refactors.
6. **Measure again.** Compare before/after numbers with the same workload or explain why only static validation was possible.
7. **Document tradeoffs.** Note any complexity, cache invalidation, concurrency limits, or environment assumptions introduced by the optimization.

Before writing code, pause and ask yourself:

1. What is the dominant cost for this workload?
2. Can I reduce algorithmic complexity, allocations, I/O round-trips, blocking, or contention?
3. How will I verify the change did not alter behavior and actually improved the target metric?

## 1. Loops and Iteration

**Every loop is a cost multiplier. Minimize what happens inside.**

- **Never recompute invariants inside a loop.** Hoist constant expressions, lengths, and lookups above the loop.
- **Avoid nested loops when a single pass with a hash map or index will do.** O(n²) is almost never acceptable when O(n) or O(n log n) exists.
- **Prefer language-native bulk operations** (map, filter, reduce, list comprehensions, vectorized ops) over manual loops when the runtime optimizes them.
- **Break early.** If you found your answer, stop iterating. Use `break`, early returns, or short-circuit evaluation.
- **Fuse loops.** If two sequential loops iterate over the same collection, merge them into one pass when logic permits.
- **Avoid allocations inside loops.** Do not create objects, strings, or arrays inside a loop body that could be created once and reused or pre-allocated.

```
// BAD — recomputes len, creates string each iteration
for (int i = 0; i < list.size(); i++) {
    String key = prefix + ":" + list.get(i).getName();
    map.put(key, list.get(i));
}

// GOOD — hoisted size, reused builder, single access
int n = list.size();
StringBuilder sb = new StringBuilder(prefix).append(':');
int prefixLen = sb.length();
for (int i = 0; i < n; i++) {
    Item item = list.get(i);
    sb.setLength(prefixLen);
    sb.append(item.getName());
    map.put(sb.toString(), item);
}
```

## 2. Variables and Temporaries

**Every variable costs a register or a stack slot. Use only what you need.**

- **Eliminate unnecessary temporaries.** If a value is used exactly once and inline use is readable, inline it.
- **Never assign a variable you don't read.** Dead stores waste cycles and confuse readers.
- **Prefer direct returns** over assigning to a temporary and then returning it, when the expression is clear.
- **Reuse accumulators** instead of building intermediate collections that are immediately discarded.

```
// BAD — pointless temporary
result = compute_value(x)
return result

// GOOD — direct return
return compute_value(x)
```

```
// BAD — builds full list just to check existence
temp = [item for item in collection if item.matches(criteria)]
found = len(temp) > 0

// GOOD — short-circuit, no allocation
found = any(item.matches(criteria) for item in collection)
```

## 3. Memory and Allocations

**Allocations are expensive. The fastest allocation is the one that never happens.**

- **Pre-allocate** collections when the size is known or estimable. Resizing arrays/lists/maps is costly.
- **Reuse buffers** for repeated operations (string building, byte buffers, temporary arrays).
- **Prefer stack allocation over heap** when the lifetime is bounded to the current scope (value types, structs, stack arrays).
- **Avoid boxing primitives** in languages that distinguish boxed/unboxed types (Java, C#, Kotlin).
- **Use object pools or arenas** for high-frequency short-lived allocations in performance-critical paths.
- **Prefer views/slices** over copying sub-arrays or substrings. Reference the original data when mutation is not needed.
- **Release references early.** Null out or reassign references to large objects as soon as they are no longer needed, especially before long-running operations.
- **Choose the right data structure size.** Don't use a `HashMap<K,V>` with default capacity 16 when you know you'll store 10,000 entries.

```
// BAD — grows the list dynamically, multiple reallocations
items = []
for row in rows:
    items.append(transform(row))

// GOOD — pre-allocated
items = [None] * len(rows)
for i, row in enumerate(rows):
    items[i] = transform(row)

// BEST — generator if downstream consumes lazily
items = (transform(row) for row in rows)
```

## 4. Algorithms and Data Structures

**The biggest performance wins come from choosing the right algorithm, not from micro-tuning the wrong one.**

- **Know your complexities.** Before writing a solution, state its Big-O for time and space. If it's worse than necessary, find a better approach.
- **Use hash-based lookups** (sets, maps, dictionaries) for membership tests and key lookups — O(1) vs O(n) linear scan.
- **Sort only when needed** and pick the right sort. Don't sort to find a min/max — just scan once.
- **Use appropriate data structures**: deques for front/back operations, heaps for top-k, tries for prefix matching, bitsets for flags.
- **Cache expensive computations.** Apply memoization for pure functions with repeating inputs. Use lookup tables for constant mappings.
- **Avoid redundant computation.** Never compute the same derived value twice in the same scope. Compute once, store, reuse.

## 5. String Operations

**Strings are deceptively expensive. Concatenation, formatting, and encoding are hidden cost centers.**

- **Use string builders / buffers** for multi-step concatenation, especially inside loops. Never concatenate with `+` in a loop.
- **Prefer interpolation or formatting** over repeated concatenation when the language optimizes it.
- **Avoid repeated parsing.** Parse a string once (to a date, number, enum, etc.) and pass the parsed value forward.
- **Compare by identity before equality** when interned strings or symbols are available.
- **Use byte-level operations** when you don't need Unicode semantics (e.g., ASCII protocol parsing).

## 6. I/O and Network

**I/O is orders of magnitude slower than computation. Batch, buffer, and minimize round-trips.**

- **Batch database queries.** Never query inside a loop (N+1 problem). Use bulk fetches, JOINs, or IN clauses.
- **Buffer I/O.** Wrap unbuffered streams in buffered wrappers. Flush strategically, not on every write.
- **Minimize network round-trips.** Combine API calls, use batch endpoints, prefetch what you'll need.
- **Use streaming** for large payloads instead of loading everything into memory.
- **Use connection pooling** for databases, HTTP clients, and any reusable connection.
- **Set appropriate timeouts.** Unbounded waits waste threads and resources.
- **Paginate large result sets** instead of loading millions of rows into memory.

```
// BAD — N+1 queries
for user in users:
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", user.id)

// GOOD — single batch query
user_ids = [u.id for u in users]
all_orders = db.query("SELECT * FROM orders WHERE user_id IN (?)", user_ids)
orders_by_user = group_by(all_orders, key=lambda o: o.user_id)
```

## 7. Concurrency and Parallelization

**Use concurrency for I/O-bound work. Use parallelism for CPU-bound work. Know the difference.**

- **Identify independent operations** and run them concurrently (async/await, futures, goroutines, threads).
- **Use async I/O** for network calls, file reads, and database queries that can overlap.
- **Parallelize CPU-bound work** across cores using thread pools, worker pools, or parallel streams — but only when the workload justifies the overhead.
- **Avoid shared mutable state.** Prefer immutable data, message passing, or lock-free structures. If you must lock, minimize the critical section.
- **Batch concurrent work** with bounded concurrency (semaphores, task queues) to avoid overwhelming resources.
- **Beware of false sharing** in cache lines when using parallel arrays or adjacent atomic counters.

```
// BAD — sequential I/O calls
result_a = await fetch(url_a)
result_b = await fetch(url_b)
result_c = await fetch(url_c)

// GOOD — concurrent I/O
[result_a, result_b, result_c] = await Promise.all([
    fetch(url_a),
    fetch(url_b),
    fetch(url_c),
])
```

## 8. Lazy Evaluation and Short-Circuiting

**Don't compute what you won't use.**

- **Use lazy evaluation** (generators, iterators, streams) when consumers may not need all results.
- **Order conditionals by cost and likelihood.** Put the cheapest, most-likely-to-short-circuit check first.
- **Defer expensive initialization** until the value is actually accessed (lazy properties, double-checked locking, `once` patterns).
- **Use pagination and limits** in queries — don't fetch all rows to display ten.

```
// BAD — evaluates expensive condition even when cheap one fails
if (expensiveCheck(x) && cheapCheck(x)) { ... }

// GOOD — cheap check first, expensive only if needed
if (cheapCheck(x) && expensiveCheck(x)) { ... }
```

## 9. Caching

**The fastest computation is the one you already did.**

- **Cache pure function results** when inputs repeat (memoization).
- **Use appropriate cache eviction** (LRU, TTL, size-bounded) to prevent unbounded memory growth.
- **Cache at the right layer.** In-memory for hot data, Redis/Memcached for shared state, HTTP caching for API responses, CDN for static assets.
- **Invalidate correctly.** Stale caches are worse than no caches. Prefer time-based expiry for data whose staleness is tolerable.
- **Profile before caching.** Only cache what is actually expensive. Caching cheap computations adds complexity for no gain.

## 10. Data Serialization and Deserialization

**Parsing and formatting data is a hidden tax on every boundary.**

- **Choose the right format.** Binary formats (Protocol Buffers, MessagePack, FlatBuffers) are faster than text formats (JSON, XML) for internal service communication. Use text formats only at system boundaries where human readability matters.
- **Serialize once.** Don't convert an object to JSON, pass the string, then parse it back on the other side of the same process. Pass the object.
- **Use streaming parsers** (SAX, `JsonReader`, `ijson`) for large payloads instead of loading the entire document into a DOM tree.
- **Avoid repeated serialization.** If the same object is serialized multiple times (e.g., for logging and for a response), serialize once and reuse the result.
- **Prefer schema-driven serialization** (protobuf, Avro) over reflection-based serialization (Java's default `Serializable`, Python's `pickle`) in performance-critical paths.
- **Be aware of encoding costs.** Base64 encoding inflates data by ~33%. Compress before encoding when payload size matters.
- **Deserialize selectively.** If you only need three fields from a 50-field JSON object, use a partial parser or projection — don't deserialize the entire object.

```
// BAD — full deserialization when only one field is needed
data = json.parse(payload)
user_id = data["user"]["id"]

// GOOD — targeted extraction (language-dependent)
user_id = json_extract(payload, "$.user.id")
```

## 11. Error Handling

**Exceptions are expensive. Never use them for control flow.**

- **Don't throw exceptions for expected conditions.** A user submitting invalid input is not exceptional — it's normal. Use result types, error codes, or validation returns.
- **Avoid try/catch in hot loops.** In most runtimes, entering a try block has overhead, and throwing is extremely expensive (stack unwinding, trace capture).
- **Prefer guard clauses** (early returns on invalid input) over wrapping entire methods in try/catch.
- **Disable stack traces for known error types** in languages that allow it (e.g., overriding `fillInStackTrace()` in Java) when the trace is never read.
- **Use error-value patterns** (`Result<T, E>`, `Option<T>`, `(value, err)` tuples) in performance-critical code instead of exception-based flow.

```
// BAD — exception as control flow in a tight loop
for item in items:
    try:
        value = int(item)
        process(value)
    except ValueError:
        continue

// GOOD — check before converting
for item in items:
    if item.isdigit():
        process(int(item))
```

## 12. Logging and Observability

**Logging is invisible overhead — until it dominates your profile.**

- **Guard expensive log messages.** Don't construct a log message string if the log level is disabled. Use lazy evaluation, lambdas, or level-check guards.
- **Never log inside a tight loop** unless at TRACE/DEBUG level and guarded by a level check.
- **Use structured logging** (key-value pairs) over string formatting. Structured loggers defer serialization until the log is actually written.
- **Use async/buffered logging** for high-throughput paths. Synchronous log writes to disk or network block the calling thread.
- **Avoid logging large objects.** Don't `toString()` an entire collection or request body at INFO level. Log identifiers and sizes instead.
- **Sample high-frequency events.** If an event fires thousands of times per second, log 1 in N instead of every occurrence.

```
// BAD — string is always constructed, even if DEBUG is off
logger.debug("Processing user " + user.toString() + " with orders " + orders.toString())

// GOOD — deferred evaluation, no construction if level is off
logger.debug("Processing user {} with {} orders", user.id, orders.size())
```

## 13. Regular Expressions

**Regex is powerful but deceptively expensive. Use the simplest tool that works.**

- **Compile once, reuse.** Never compile a regex pattern inside a loop or on every function call. Compile it as a constant, `static final`, or module-level variable.
- **Prefer simple string methods** (`startsWith`, `endsWith`, `contains`, `indexOf`, `split`) when the match is literal or trivially simple.
- **Avoid catastrophic backtracking.** Nested quantifiers like `(a+)+` or `(a|a)+` cause exponential time. Use atomic groups or possessive quantifiers when available.
- **Use non-capturing groups** `(?:...)` instead of capturing groups `(...)` when you don't need the match value — capturing allocates memory.
- **Anchor your patterns.** Use `^` and `$` anchors to prevent the engine from scanning the entire string unnecessarily.
- **Benchmark complex patterns** against hand-written parsers. For high-frequency parsing (logs, protocols), a state machine often outperforms regex.

```
// BAD — recompiles regex on each call
def extract_email(text):
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    return match.group(0) if match else None

// GOOD — compiled once at module level
EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

def extract_email(text):
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None
```

## 14. Resource Lifecycle

**Leaked resources are slow-motion performance degradation.**

- **Always close what you open.** Use language-provided patterns: `try-with-resources` (Java), `using` (C#), `with` (Python), `defer` (Go), RAII (C++/Rust).
- **Scope resources tightly.** Open a file, database connection, or lock at the latest moment and release it at the earliest. Don't hold resources across long-running operations.
- **Avoid finalizers and destructors for cleanup.** They run unpredictably (or never) and add GC overhead. Use deterministic cleanup.
- **Watch for connection leaks.** Every un-returned database connection, HTTP client, or socket exhausts a pool and eventually stalls everything.
- **Limit resource consumption.** Apply bounded queues, rate limits, max-connection counts, and memory caps to prevent uncontrolled growth.

```
// BAD — connection leak if process() throws
conn = pool.get_connection()
result = process(conn)
conn.close()

// GOOD — guaranteed cleanup
with pool.get_connection() as conn:
    result = process(conn)
```

## 15. Data Locality and Cache-Friendliness

**The fastest data is the data already in the CPU cache.**

- **Access memory sequentially.** Iterating an array linearly is dramatically faster than chasing pointers through a linked list or tree due to cache prefetching.
- **Keep hot data together.** Group fields that are accessed together into the same struct/object. Separate rarely-accessed fields into auxiliary structures.
- **Prefer arrays/vectors over linked structures** (linked lists, trees with pointer-per-node) when traversal order is predictable.
- **Consider Struct-of-Arrays (SoA) over Array-of-Structs (AoS)** when you process one field across many entities (common in data-heavy or game/simulation code).
- **Minimize pointer indirection.** Each pointer chase is a potential cache miss. Flatten nested objects when feasible.
- **Be aware of memory alignment and padding.** Order struct fields by size (largest first) to minimize padding waste in languages where layout is controllable.
- **Use contiguous allocations.** Pre-allocate flat buffers or arenas for objects that are created and processed together.

```
// SLOW — random access pattern, poor locality
for node in linked_list:
    total += node.value     // each node is a pointer chase

// FAST — sequential access, cache-friendly
for i in range(len(values)):
    total += values[i]      // contiguous memory, hardware prefetch
```

## 16. Language-Specific Awareness

**Know the performance characteristics of the language you are using.**

This skill is language-agnostic, but the agent must apply language-specific knowledge when relevant:

- **JVM (Java, Kotlin, Scala):** Avoid autoboxing, prefer primitive streams, be aware of GC pressure, use `StringBuilder`, choose the right collection implementation.
- **Python:** Use generators over lists, prefer `collections` module types, use NumPy/pandas for vectorized computation, avoid global interpreter lock for CPU parallelism (use multiprocessing).
- **JavaScript/TypeScript:** Avoid megamorphic call sites, prefer typed arrays for numeric work, use Web Workers for CPU-bound tasks, be aware of event loop blocking.
- **Go:** Minimize allocations that escape to heap, use sync.Pool for reusable objects, prefer value receivers for small structs, use goroutines with bounded concurrency.
- **Rust:** Prefer stack allocation, use iterators over indexed loops, avoid unnecessary cloning, leverage zero-cost abstractions.
- **C/C++:** Consider cache locality (struct of arrays vs array of structs), use SIMD where applicable, prefer move semantics over copies, minimize virtual dispatch in hot paths.
- **SQL:** Use indexes, avoid SELECT *, use EXPLAIN to understand query plans, prefer set-based operations over cursors.
- **PHP:** Prefer native array functions over manual loops, use generators for large datasets, avoid unnecessary object instantiation, use opcache effectively.
- **C#/.NET:** Use `Span<T>` and `Memory<T>` to avoid allocations, prefer `ValueTask` for hot async paths, use `ArrayPool` for temporary buffers, avoid LINQ in hot paths due to delegate overhead.

## 17. What NOT to Optimize

**Premature optimization is the root of all evil — but so is willful negligence.**

Do not micro-optimize at the cost of readability when:
- The code runs once (scripts, migrations, setup).
- The operation is already sub-millisecond and not in a hot path.
- A profile shows the bottleneck is elsewhere.

**But always optimize when:**
- The code runs in a loop, a request handler, or a hot path.
- The operation involves I/O, network, or large data.
- The choice between efficient and inefficient is equally readable (prefer the efficient one by default).
- You can use a better algorithm or data structure with no added complexity.

## Applying This Skill

When writing or reviewing code, follow this checklist:

1. **Identify the hot path.** Where will this code run most frequently?
2. **Choose the right algorithm.** Is the Big-O optimal for the problem?
3. **Minimize allocations.** Can you pre-allocate, reuse, or avoid creating objects?
4. **Eliminate redundant work.** Are you computing anything twice? Can you cache it?
5. **Batch I/O.** Are you making unnecessary round-trips to disk, network, or database?
6. **Exploit concurrency.** Are there independent operations that can run in parallel?
7. **Short-circuit early.** Can you exit loops, conditions, or functions early?
8. **Guard your logs.** Is log message construction deferred behind level checks?
9. **Serialize once.** Are you converting data back and forth unnecessarily across boundaries?
10. **Handle errors cheaply.** Are exceptions used for control flow in hot paths?
11. **Close your resources.** Are connections, handles, and locks released deterministically?
12. **Think about locality.** Is the data layout cache-friendly for the access pattern?
13. **Validate with data.** When in doubt, profile. Don't guess where the bottleneck is.

> **Every line of code has a cost. Spend complexity only where the workload earns it.**

## Quick Start Workflow

1. **Analyze**: Identify the hot path, bottleneck, and target metric using profiling tools or justified code inspection.
2. **Refactor**: Apply the smallest effective change: better complexity, fewer allocations, batching, streaming, indexing, caching, bounded concurrency, or reduced synchronization.
3. **Validate**: Run correctness checks and compare before/after performance with the same workload when feasible.

## Validation And Completion

The skill has been applied successfully when:

- The target metric and workload are stated, or the agent explicitly explains the assumption used.
- The likely bottleneck is identified with profiler data, benchmark data, query plans, logs, traces, or clear complexity analysis.
- The implementation preserves observable behavior and keeps existing tests passing.
- The optimization is scoped to the bottleneck and avoids unrelated rewrites.
- Before/after evidence is reported when measurement is possible, including the command, workload, sample size, and result.
- If benchmark noise or environment limits make results uncertain, the final answer says so and avoids overstating the gain.

Use the repository's existing performance tools when available: benchmark suites, load tests, profilers, database `EXPLAIN`, flamegraphs, browser performance tooling, memory profilers, or runtime tracing. Do not add a new benchmarking framework unless it fits the project and the user asked for durable performance tests.

## Failure And Escalation Behavior

Ask the user for clarification or stop instead of guessing when:

- The target workload, expected scale, or performance metric is essential but unknown.
- A proposed optimization changes user-visible behavior, data consistency, ordering, security, accessibility, or compatibility.
- The only plausible improvements require architectural changes, new infrastructure, paid services, schema migrations, or operational risk.
- Existing tests are absent and the code path is too risky to optimize without first adding or requesting correctness coverage.

When performance is not relevant to the user's request, do not force this skill. Prefer normal repository conventions while still choosing efficient code when it is equally simple.

## Output Expectations

When finishing a performance task, include:

- The bottleneck or risk addressed.
- The optimization made and why it should improve the target metric.
- Correctness checks run.
- Performance checks run, with before/after results when available.
- Residual risks, measurement limits, or follow-up profiling targets.

## Reference Documentation

This skill follows general performance principles. No external references are required at this time.

## Scripts and Assets

- `assets/behavior-fixtures.json` - behavior fixtures for performance activation, non-activation, measurement, and validation guidance.
- `scripts/validate-fixtures.js` - validates that this skill and its behavior fixtures cover required performance-optimization boundaries.

## License information

This skill is licensed under the [MIT License](LICENSE).

