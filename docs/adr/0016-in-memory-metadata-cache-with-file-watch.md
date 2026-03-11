# ADR 0016: In-Memory Metadata Cache with File-Change Detection

- Status: Proposed
- Date: 2026-03-10

## Context

Every web request that needs record data calls `read_metadata()`, which opens `metadata.json`, deserializes the full JSON array, and deep-copies every record. On a library with 100 records, this means:

- **Disk I/O on every request:** even when no records have changed since the last read.
- **Repeated deserialization:** `json.load()` parses the same bytes on every hit.
- **Deep-copy overhead:** `copy.deepcopy()` traverses every nested dict and list to produce a detached snapshot.

The mutation path (`mutate_metadata`) already uses file-level locking (`fcntl.flock`) and atomic writes (`os.replace`), so the write side is safe. But the read side pays the full cost unconditionally.

For multi-worker deployments (e.g. `uvicorn --workers 4`), each worker independently re-reads the file because there is no shared cache layer.

## Decision

1. **Singleton in-memory cache.** Introduce a `MetadataCache` class that holds the deserialized record list in memory. Expose `cache.records()` which returns a shallow copy of the cached list (individual record dicts are treated as immutable between mutations).

2. **`mtime` + `size` invalidation.** On each `records()` call, `os.stat()` the metadata file and compare `st_mtime_ns` and `st_size` to the cached values. If unchanged, return the cached list in O(1). If changed, re-read and re-cache. `os.stat()` is a single syscall and is orders of magnitude cheaper than `json.load()`.

3. **Write-through on mutation.** When `mutate_metadata()` successfully writes the file, it also updates the cache in-place so that the writing worker sees the new state without a re-read.

4. **Per-worker cache, not cross-process.** Each uvicorn worker maintains its own `MetadataCache` instance. Workers discover changes made by other workers through `mtime` diffing. This avoids the complexity of shared-memory or Redis for what is still a file-backed metadata store.

5. **Cache warming at startup.** During FastAPI `lifespan` startup, call `cache.warm()` to pre-load metadata so the first request is not penalised.

## Consequences

- **Benefits:** Repeat reads during a single request cycle (e.g. index page + progress enrichment + workflow metrics) all hit the cache. JSON parsing drops from once-per-request to once-per-write. Perceived latency of the index page drops measurably for libraries with 50+ episodes.
- **Tradeoffs:** Slightly stale reads are possible in multi-worker mode (up to the mtime polling granularity, typically < 10 ms). This is acceptable because metadata staleness for a few milliseconds has no user-visible effect.
- **Risks:** If an external process modifies `metadata.json` without going through `mutate_metadata()`, the cache will still detect it via `mtime`. If the file is replaced on a filesystem that does not update `mtime` reliably (rare edge case), stale data could persist until the next write. Mitigate by adding a periodic `os.stat()` in a background task if needed.
- **Follow-up:** This cache pattern lays groundwork for a future migration to SQLite (ADR to follow), where the in-memory cache becomes an ORM session cache and the invalidation logic is replaced by WAL-based change detection.
