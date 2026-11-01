---
name: "Storage"
description: "Equipment's local and S3 storage API, verified differences between the two drivers, path safety, data encoding, error handling, and testing."
tags: [equipment, storage, StorageFactory, LocalStorage, S3Storage, AbstractStorage, boto3, s3, moto, path, write, read, exists, remove, move, list, path-traversal, FILESYSTEM_DISK, S3_PREFIX]
---

# Storage

`application.storage()` returns a `StorageFactory` that wraps one driver selected by `FILESYSTEM_DISK`: `local` or `s3`. Use it for application-managed files such as reports, exports, uploads, and cache files that may move from local disk to S3 later.

## Configuration

```yaml
storage:
  disk: ${FILESYSTEM_DISK:local}   # "local" or "s3"
  disks:
    local:
      path: storage/app
    s3:
      endpoint: ${S3_ENDPOINT}
      bucket: ${S3_BUCKET}
      access_key: ${S3_ACCESS_KEY}
      secret_key: ${S3_SECRET_KEY}
      region: ${S3_REGION:auto}
      prefix: ${S3_PREFIX:null}
```

- The local key is `path`, not `root`. The root is `os.path.join(base_path, path)`. An absolute `path` replaces the base path entirely.
- The S3 driver creates a `boto3` S3 client lazily with the endpoint, keys, and region. Unset values arrive as `None`, which lets `boto3` use its default endpoint and credential chain.
- `S3_PREFIX` values `None`, `null`, and empty mean no prefix. Otherwise the prefix plus `/` is prepended to every key. With `S3_PREFIX=production`, `write("reports/a.txt", ...)` writes `production/reports/a.txt`.
- Any other `FILESYSTEM_DISK` raises `ValueError: Unknown storage type: <value>`.

## API

| Method | Returns | Notes |
|---|---|---|
| `path(file)` | `str` | Local: absolute filesystem path. S3: object key including the prefix. |
| `write(file, data)` | `bool` | Errors are logged and return `False`. |
| `read(file)` | `str` | Raises `FileNotFoundError` when missing. |
| `exists(file)` | `bool` | |
| `remove(file)` | `bool` | Errors are logged and return `False`. |
| `move(source, destination)` | `bool` | Errors are logged and return `False`. |
| `list(path)` | `list` | Names relative to `path`. Behavior differs by driver. |

## Verified Driver Differences

Code that passes on one driver can fail on the other:

| Operation | `local` | `s3` |
|---|---|---|
| `write(file, str)` | Creates parent directories, writes UTF-8 text. | `put_object`. |
| `write(file, bytes)` | Returns `False` (text mode). | Returns `True`; `read()` later decodes as UTF-8. |
| `move()` into a directory that does not exist | Returns `False` (`os.rename` does not create directories). | Works; S3 has no directories (copy, then delete). |
| `list("dir")` | Direct files only, not subdirectories. | Every key under the prefix, recursively, as relative names such as `sub/b.txt`. |
| `list("missing")` | Raises `NotADirectoryError`. | Returns `[]`. |
| `list("")` on the root | Includes `.gitignore` in the generated project. | With `S3_PREFIX` set: every key under the prefix. Without a prefix: names are corrupted, because the first `/` of each key is removed (`sub/b.txt` becomes `subb.txt`, verified). |
| `exists()` on errors | Filesystem check. | Returns `False` for any error, including permission and network errors (logged). |
| `read()` on errors | `FileNotFoundError` when missing. | `FileNotFoundError` for missing keys and for other client errors such as `403` (logged first). |
| Atomicity | `move()` is a filesystem rename. | `move()` is copy then delete, not atomic. |

The docs' example `storage.move("reports/today.txt", "reports/archive/today.txt")` returns `False` on the local driver unless `reports/archive/` already exists. A driver-neutral move for text files:

```python
from equipment.Storage.AbstractStorage import AbstractStorage


def move_text(storage: AbstractStorage, source: str, destination: str) -> None:
    if not storage.write(destination, storage.read(source)):
        raise RuntimeError(f"Could not write {destination}")
    if not storage.remove(source):
        raise RuntimeError(f"Could not remove {source}")
```

## Path Safety

Verified on the local driver:

- `write("../escaped.txt", ...)` writes outside the storage root.
- `path("/absolute/file.txt")` returns `/absolute/file.txt`; an absolute path discards the root.

Never pass raw user input as a storage path. Generate the name and keep only a sanitized label:

```python
import re
import uuid


def upload_path(user_id: int, original_name: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]", "_", original_name)[:100].lstrip(".") or "file"
    return f"uploads/{int(user_id)}/{uuid.uuid4().hex}-{label}"
```

Use relative paths with `/` separators. Avoid leading slashes, drive letters, `..` segments, and backslashes.

## Data Encoding

Storage methods are designed for strings. Serialize structured data explicitly:

```python
import json

application.storage().write("reports/status.json", json.dumps({"status": "ready"}))
status = json.loads(application.storage().read("reports/status.json"))
```

For binary data, encode it so both drivers behave the same, or extend the storage layer in your application:

```python
import base64

application.storage().write("images/logo.b64", base64.b64encode(raw_bytes).decode("ascii"))
raw = base64.b64decode(application.storage().read("images/logo.b64"))
```

## Error Handling

```python
if not application.storage().write(path, content):
    application.log().error("Could not write file", extra={"path": path})
    raise RuntimeError("Storage write failed")

try:
    content = application.storage().read(path)
except FileNotFoundError:
    content = None
```

The storage layer provides no locks, versioning, or compare-and-swap. Coordinate concurrent writers with database records, object versioning, or a queue.

## Choosing A Driver

- `local`: development, tests, single-machine scripts, files that are not shared between servers.
- `s3`: user uploads, exports, files shared between web servers and workers, platforms without persistent disks.
- Do not use `local` for horizontally scaled apps unless every process shares the same filesystem.

## Testing

Point local storage at a temporary directory with a reversible config override, and rebuild the storage singleton (verified):

```python
import shutil
import tempfile

from tests.TestCase import TestCase


class ReportsStorageTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        self.enterContext(self.app.config.storage.disk.override("local"))
        self.enterContext(self.app.config.storage.disks.local.path.override(root))
        self.app.storage.reset()
        self.addCleanup(self.app.storage.reset)

    def test_write_then_read(self) -> None:
        self.assertTrue(self.app.storage().write("reports/a.txt", "A"))
        self.assertEqual("A", self.app.storage().read("reports/a.txt"))
```

Without this, tests write into the project's `storage/app/` directory.

Use `moto` for S3 unit tests. It validates bucket names, so use a valid name such as `test-bucket` (a one-letter name fails with `InvalidBucketName`):

```python
import boto3
from moto import mock_aws

from equipment.Log.NullLogger import NullLogger
from equipment.Storage.S3Storage import S3Storage


with mock_aws():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    storage = S3Storage(
        {"endpoint": None, "bucket": "test-bucket", "access_key": "k", "secret_key": "s",
         "region": "us-east-1", "prefix": "test"},
        NullLogger(),
    )
    assert storage.write("a.txt", "A")
```

`moto` is a dependency of the `equipment` package, so it is installed alongside it. Keep real-bucket tests separate and opt-in.

Cover both success and failure paths: write then read, missing read, nested writes, moves into new directories, listing, and prefix handling.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| File in an unexpected directory | Wrong base path, `FILESYSTEM_DISK`, or absolute `path`. | Run from the project root; check `config/storage.yaml`. |
| `move()` returns `False` locally | Destination directory missing. | Write the destination, then remove the source. |
| `NotADirectoryError` from `list()` | Local directory does not exist (S3 returns `[]` instead). | Catch it and treat it as empty; `exists()` only checks files. |
| S3 key has an unexpected prefix | `S3_PREFIX` is set. | Unset it, or set `null`. |
| S3 `list("")` returns names such as `subb.txt` | No `S3_PREFIX`; the root listing strips the first `/` of each key. | List a named directory (`list("sub")`), or set `S3_PREFIX`. |
| `exists()` is always `False` on S3 | Credentials, region, endpoint, or network errors are reported as `False`. | Check logs for the logged client error. |
| `write()` returns `False` locally with bytes | Local driver writes text only. | Encode binary data, or use S3 consistently. |

## Best Practices

- Use `app.storage()` instead of `open()` for application-managed files.
- Generate storage paths; never pass raw user input.
- Write code that works on both drivers: text data, write-then-remove moves, and no reliance on `list()` recursion.
- Check boolean results and handle `FileNotFoundError`.
- Isolate storage in tests with a temporary root and reset the singleton.
- Use shared storage (S3) when more than one process or server reads the files.
