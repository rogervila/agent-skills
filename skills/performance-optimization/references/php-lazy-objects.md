---
name: "PHP 8.4+ Lazy Objects (Ghosts and Proxies)"
description: "When and how to defer expensive PHP object initialization with native lazy ghosts and lazy proxies, including triggers, pitfalls, and measurement."
tags: [php, php84, lazy-objects, lazy-ghost, lazy-proxy, newLazyGhost, newLazyProxy, resetAsLazyGhost, resetAsLazyProxy, initializeLazyObject, isUninitializedLazyObject, markLazyObjectAsInitialized, setRawValueWithoutLazyInitialization, skipLazyInitialization, SKIP_INITIALIZATION_ON_SERIALIZE, SKIP_DESTRUCTOR, dependency-injection, orm, deferred-initialization]
---

# PHP 8.4+ Lazy Objects (Ghosts and Proxies)

PHP 8.4 added native lazy objects to the Reflection API. A lazy object looks and type-checks like a normal instance of its class, but its state is built only when code first touches that state. This replaces hand-written virtual proxies, code-generated proxy classes, and userland traits such as `symfony/var-exporter`'s `LazyGhostTrait`.

Use this reference when a PHP project runs on PHP 8.4 or later and a profile, trace, or clear code inspection shows that objects are built but often never used.

## Version Gate

Native lazy objects exist only in PHP 8.4 and later. Before using them, confirm all of these:

- `composer.json` requires `"php": ">=8.4"` (or a narrower range starting at 8.4).
- CI, Docker images, and production run PHP 8.4 or later.
- The code does not have to run on older PHP versions.

If the project supports PHP 8.3 or earlier, do not use these APIs. Use the existing lazy mechanism of the framework, a closure-based factory, or a hand-written proxy instead. If a shared library must support both, guard the call:

```php
if (PHP_VERSION_ID >= 80400) {
    $service = (new ReflectionClass(Mailer::class))->newLazyGhost($initializer);
} else {
    $service = $legacyFactory();
}
```

> Prefer one code path. Add a version branch only when the package really must support both runtimes.

## When Laziness Helps

Laziness moves cost. It does not remove cost. It only wins when the object is often not used, or when moving the cost off a latency-critical path matters.

| Good fit | Poor fit |
|---|---|
| Services with expensive constructors (DB connections, HTTP/SDK clients, template engines) that many requests never call | Small value objects or DTOs that are cheap to build |
| ORM entities or aggregates referenced by ID but rarely read | Objects that are read on every request anyway |
| Large config, metadata, or translation trees where most requests read a small part | Objects created inside a tight loop where the per-object overhead matters |
| Speeding up CLI/worker boot or framework container warm-up | Code where deferred errors (failed connection at first use) are unacceptable |
| Graphs where only some branches are traversed | Objects whose constructor has side effects the caller relies on immediately |

Before adding laziness, measure how often the object is actually used. If it is used in more than a small fraction of requests, the lazy wrapper adds overhead and indirection for no gain.

## Ghost vs Proxy

| | Lazy ghost | Lazy proxy |
|---|---|---|
| API | `ReflectionClass::newLazyGhost(callable $initializer, int $options = 0)` | `ReflectionClass::newLazyProxy(callable $factory, int $options = 0)` |
| Callback signature | `function (object $object): void` | `function (object $proxy): object` |
| What happens on first use | The initializer fills the same object in place | The factory returns a separate real instance; the proxy forwards property access to it |
| Object identity | One object; identity is preserved | Two objects: proxy and real instance are `!==` |
| Who creates the instance | You control construction | Construction is done by a factory you do not control |
| Default choice | Yes | Only when a ghost is not possible |

Prefer ghosts. They keep a single identity, have less indirection, and avoid bugs where the real instance leaks `$this` (for example, it registers itself in an event dispatcher or identity map) and code ends up holding two different objects.

Use a proxy when the real instance must come from somewhere else: a third-party factory, a builder, a container, or a deserializer.

## Lazy Ghost

```php
final class ReportRenderer
{
    public function __construct(
        private TemplateEngine $engine,
        private array $templates,
    ) {
        // Expensive: compiles templates, opens cache files, etc.
    }

    public function render(string $name, array $data): string
    {
        return $this->engine->render($this->templates[$name], $data);
    }
}

$reflector = new ReflectionClass(ReportRenderer::class);

$renderer = $reflector->newLazyGhost(function (ReportRenderer $ghost): void {
    // Runs once, on first access to any property of $ghost.
    $ghost->__construct(new TemplateEngine(), loadTemplates());
});

// No construction cost has been paid yet.
// The first render() reads $this->engine, which triggers the initializer.
echo $renderer->render('invoice', $data);
```

Rules for ghost initializers:

- The initializer must return `null` or nothing. Returning a value throws `TypeError: Lazy object initializer must return NULL or no value`.
- Calling `$ghost->__construct(...)` from inside the initializer is the normal pattern. It also works for `readonly` properties.
- If the initializer throws, the object goes back to its uninitialized state. The next access calls the initializer again.

## Lazy Proxy

```php
$reflector = new ReflectionClass(S3Client::class);

$client = $reflector->newLazyProxy(function (S3Client $proxy): S3Client {
    // A factory we do not control builds the real instance.
    return S3ClientFactory::fromEnvironment();
});

$client->putObject($args); // first property access creates and forwards to the real instance
```

Rules for proxy factories:

- The factory must return a non-lazy instance of the proxy's class, or of a parent class.
- If the proxy class is a subclass of the real instance's class, it must not declare extra properties and must not override `__destruct()` or `__clone()`. Otherwise PHP throws a `TypeError`.
- `ReflectionClass::initializeLazyObject($proxy)` returns the real instance. Avoid exposing it: callers that compare identity with `===` will see two objects.

## What Triggers Initialization

Initialization is triggered by access to object state, not by having the object or calling its methods.

| Triggers initialization | Does not trigger initialization |
|---|---|
| Reading or writing a lazy property (also from inside a method) | Calling a method that does not touch lazy properties |
| `isset()` / `unset()` on a lazy property | `instanceof`, type checks, `get_class()`, `spl_object_id()` |
| `foreach` over the object, `get_object_vars()` | `(array)` cast, `var_dump()` |
| `json_encode()`, `var_export()` | `ReflectionClass::isUninitializedLazyObject()` |
| `serialize()` (unless `SKIP_INITIALIZATION_ON_SERIALIZE`) | `ReflectionProperty::setRawValueWithoutLazyInitialization()` |
| `clone` | `ReflectionProperty::skipLazyInitialization()` |
| `ReflectionClass::initializeLazyObject()` | `ReflectionClass::markLazyObjectAsInitialized()` (marks it initialized with default values, without calling the initializer) |

Because debugging and logging helpers such as `json_encode()` and `get_object_vars()` initialize the object, a stray log statement can cancel the whole optimization. Check log and serializer paths.

## Eager Identifier, Lazy State

The most common ORM and repository pattern: the ID is known now, the rest is loaded on demand. Set the ID without triggering initialization, so reading it stays free.

```php
final class Customer
{
    public int $id;
    public string $name;
    public string $email;
}

function customerReference(int $id, CustomerLoader $loader): Customer
{
    static $reflector = new ReflectionClass(Customer::class);

    $customer = $reflector->newLazyGhost(function (Customer $ghost) use ($loader): void {
        $row = $loader->fetch($ghost->id); // $id is already set, so this does not recurse
        $ghost->name = $row['name'];
        $ghost->email = $row['email'];
    });

    $reflector->getProperty('id')->setRawValueWithoutLazyInitialization($customer, $id);

    return $customer;
}

$customer = customerReference(42, $loader);
echo $customer->id;   // 42, no query
echo $customer->name; // first query happens here
```

> Do not re-assign a property in the initializer that was already set with `setRawValueWithoutLazyInitialization()` if it is `readonly`. Assigning an initialized readonly property throws.

## Reusing Existing Objects

`resetAsLazyGhost()` and `resetAsLazyProxy()` turn an existing instance back into a lazy object. Use them to refresh pooled or long-lived objects (for example, in workers) without allocating new ones, or to make an object lazy after a framework already created it.

```php
$reflector = new ReflectionClass(Settings::class);

// By default, reset calls Settings::__destruct() first. SKIP_DESTRUCTOR prevents that.
$reflector->resetAsLazyGhost($settings, function (Settings $ghost): void {
    $ghost->__construct(loadSettings());
}, ReflectionClass::SKIP_DESTRUCTOR);
```

## Options and Helper Methods

| API | Use |
|---|---|
| `ReflectionClass::SKIP_INITIALIZATION_ON_SERIALIZE` | `serialize()` writes only already-initialized properties and does not call the initializer |
| `ReflectionClass::SKIP_DESTRUCTOR` | With `resetAsLazy*()`, do not call the destructor of the object being reset |
| `ReflectionClass::isUninitializedLazyObject($object)` | Check state in tests and metrics without initializing |
| `ReflectionClass::initializeLazyObject($object)` | Force initialization (warm-up); returns the real instance for proxies |
| `ReflectionClass::markLazyObjectAsInitialized($object)` | Mark initialized with default property values, without calling the initializer |
| `ReflectionClass::getLazyInitializer($object)` | Read the initializer or factory, mostly for tooling |
| `ReflectionProperty::setRawValueWithoutLazyInitialization($object, $value)` | Set one property eagerly; it no longer triggers initialization |
| `ReflectionProperty::skipLazyInitialization($object)` | Give one property its default value and exclude it from lazy initialization |

## Limitations

- Internal classes cannot be lazy, and neither can user classes that extend an internal class. `stdClass` is the exception. Example error: `Cannot make instance of internal class lazy: ArrayObject is internal`.
- Errors move to first use. A misconfigured DSN fails at the first query, not at boot. Keep config validation eager when fast failure matters.
- Hidden I/O moves into property reads. Code that looks like a field access can now block on a network call.
- A proxy has two identities. Anything that stores `spl_object_id()`, uses `SplObjectStorage`, or compares with `===` can behave differently.

## Pitfalls That Hurt Performance

- **Lazy N+1.** A loop over 1,000 lazy entities that reads one non-ID property runs 1,000 initializers, often 1,000 queries. Batch-load the needed rows first, or do not make that collection lazy.
- **Accidental initialization.** `json_encode()`, `get_object_vars()`, `foreach`, `clone`, debug logging, and serializers initialize the object. Audit these paths.
- **Laziness everywhere.** Wrapping objects that are always used adds Reflection setup and an extra indirection with no gain.
- **Heavy captured state.** The initializer closure keeps its captured variables alive until initialization runs. Capture IDs and small services, not large arrays.
- **Duplicated framework laziness.** Symfony and Doctrine already use native lazy objects on PHP 8.4 in recent versions (for example, Doctrine ORM through `Configuration::enableNativeLazyObjects()`). Check and enable the framework option before writing custom lazy code.

## Measuring the Effect

Measure how many lazy objects are actually initialized, and the time and memory before and after.

```php
$start = hrtime(true);
$memoryBefore = memory_get_usage();

$services = buildServices(); // eager vs lazy version

handleRequest($services);

$elapsedMs = (hrtime(true) - $start) / 1e6;
$memoryKb = (memory_get_peak_usage() - $memoryBefore) / 1024;

$reflector = new ReflectionClass(Mailer::class);
$used = !$reflector->isUninitializedLazyObject($services->mailer);

printf("%.2f ms, %.1f KiB, mailer initialized: %s\n", $elapsedMs, $memoryKb, $used ? 'yes' : 'no');
```

Run the same workload several times for both versions, or use the project's benchmark tool (PHPBench, Blackfire, Xdebug/SPX profiles). Report the initialization rate together with the timing. A high rate means laziness is not worth keeping.

## Best Practices

- Confirm PHP 8.4+ in `composer.json` and every runtime before using these APIs.
- Prefer lazy ghosts. Use lazy proxies only when another factory must create the real instance.
- Make an object lazy only when a measurement shows it is often unused, or its construction is on a latency-critical path.
- Set identifiers with `setRawValueWithoutLazyInitialization()` so cheap reads stay cheap.
- Batch-load data before loops that would initialize many lazy objects.
- Keep fail-fast validation eager. Do not hide config errors behind laziness.
- Assert laziness in tests with `isUninitializedLazyObject()`, so a later change does not silently initialize the object.
- Use the framework's native lazy-object support before writing custom Reflection code.
