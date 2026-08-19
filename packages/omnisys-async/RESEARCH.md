# OMNISYS.async — Research & Design Notes (v6 Phase 1)

Research gate for the **async** module (spec §17.8, `docs/architecture/19-quality-gates.md` §6).
Studies the relevant concurrency ecosystems and records the design decisions for the Python
reference implementation.

---

## 1. Purpose of the module

`async` provides the portable concurrency vocabulary: `task`, `delay`, `all`, `race`, `any`,
`timeout`, and a bounded FIFO `channel`. The OmniScript surface is synchronous, so these
return *Task values* that runtime tooling consumes; in the Python lane those are awaitables.
A future "advanced" mode (distributed actors, clustering) builds on this module.

---

## 2. Studied ecosystems

| Ecosystem | What it contributes |
|-----------|---------------------|
| Python `asyncio` | The host implementation: `gather`, `wait`, `wait_for`, `Queue`, `ensure_future`. |
| Rust `Tokio` | The `JoinHandle`/`select!`/`mpsc` channel design that motivates bounded channels and `race`-style selection. |
| Go goroutines + channels | The "channels are values; send/recv block" model the registry's `channel` API adopts. |
| JS Promises | `Promise.all`/`Promise.race`/`Promise.any` — the exact semantics the registry mirrors (`omnisys/async.js`). |
| Erlang/actor model | Background for the future distributed mode: message passing, supervision, clustering. |

---

## 3. The §17.3 eleven questions

1. **What problem is it solving?** Composable, portable concurrency without exposing any
   host scheduler.
2. **Which concepts survived?** Task (a scheduled computation), delay, fan-out combinators
   (`all`/`race`/`any`), timeout, bounded FIFO channel.
3. **Which exist due to historical constraints?** `Promise.any`'s reject-only-when-all-fail
   semantics; the never-settling `Promise.race([])` on an empty list.
4. **Which APIs are awkward due to the host language?** JS single-threaded event loop vs
   Python's asyncio; thread-based Go channels vs asyncio single-loop; callback-only APIs.
5. **Which abstractions are hard for AI agents?** Naming: "which awaitable do I pass?"
   Solved by a uniform Task-as-awaitable model and 10 named functions.
6. **Which concepts become first-class Omni concepts?** Task, Channel, and the combinators —
   with `uses network` on the future distributed mode.
7. **Which remain libraries?** Scheduler policies (work-stealing), OS threads, process pools.
8. **Which map to the effect/capability system?** The registry declares `core` deps only;
   the advanced (distributed) mode will declare `uses network`.
9. **What belongs in the portable semantic layer?** The whole module: task/channel/combiner
   semantics are backend-independent.
10. **What must remain backend-specific?** Thread pools, event loop configuration, OS I/O.
11. **What is the escape hatch?** The raw `asyncio.Queue`/`asyncio.Task` inside the channel
    dict and the underlying awaitables are reachable for host code that needs more.

---

## 4. Strengths / weaknesses of the ecosystems studied

- **Python asyncio**: mature, single-loop, composable. Weakness: coroutine objects are
  single-shot (awaiting twice is an error) — hidden behind combinators.
- **Rust Tokio**: superb backpressure and structured concurrency, but ownership/`'static`
  makes agent-written code heavy.
- **Go channels**: the cleanest channel ergonomics, but no structured fan-out combinators
  in the core library.
- **JS Promises**: the API the registry mirrors; `any`/`race`/`all` are familiar but the
  lack of a built-in Channel (pre-`streams`) pushes users to libraries.

---

## 5. Performance model

All combinators are O(tasks). `delay`/`channel` are allocation-light. The channel is
`asyncio.Queue` (a deque + condition), which is the standard bounded-FIFO primitive.

## 6. Ergonomics

Ten flat functions mirror the JS lane exactly. Tasks are created with `task(fn)` and are
awaitable; combinators accept lists of awaitables. No executor threads are exposed.

## 7. Type-system interaction

Generic `Awaitable[T]` everywhere; mypy `--strict` validates the registry signatures.
`channel` returns `dict[str, Any]` (the portable tagged shape) with the queue as the
`'queue'` value — reachable for escape-hatch use.

## 8. Portability

Semantics are portable; the Python lane uses asyncio, the JS lane uses Promises. Tests
never depend on wall-clock exactness beyond generous bounds.

## 9. Lifecycle / cancellation / error / concurrency model

- `task(fn)` never touches the loop at call time (returns a coroutine), so it is safe to
  build task lists outside a running loop.
- `timeout` cancels the inner task on expiry and raises `asyncio.TimeoutError`.
- `race` resolves on first completion (error or value), `any` on first success (error only
  if all fail — mirroring `Promise.any`).
- Channels are single-loop (asyncio is single-threaded); producers/consumers interleave
  on awaits.

## 10. AI usability

Named, typed, deterministic combinators; one way to do each thing. The empty/all-failed
cases are explicit (`PanicError` / re-raised first exception) rather than silent hangs.

## 11. Interop requirements

The channel dict exposes the underlying `asyncio.Queue`; tasks are real awaitables, so
they compose with any asyncio code (asyncio.gather, wait_for, etc.).

---

## 12. Concrete design decisions for this Python implementation

1. **Tasks are coroutine objects, not `asyncio.Task`s** — `task(fn)` returns an inner
   `async def _run()` coroutine so it can be created without a running loop (mirroring the
   JS `Promise.resolve().then(fn)` which also needs no loop).
2. **`all` uses `asyncio.gather`** — preserves order, fails fast on the first error
   (mirrors `Promise.all`).
3. **`race` uses `asyncio.wait(FIRST_COMPLETED)`** — resolves with whichever task completes
   first, propagating its result or error. Empty input panics (`async.race on empty list`)
   instead of hanging forever like JS.
4. **`any` loops `FIRST_COMPLETED` skipping failures** — the first successful result wins;
   if all fail, the first exception is re-raised (mirrors `Promise.any`'s aggregate reject).
   Empty input panics.
5. **`timeout` uses `asyncio.wait_for`** — raises `asyncio.TimeoutError` on expiry, which
   the registry surfaces as the timeout failure mode.
6. **Channel = `{"tag": "channel", "capacity": N, "queue": asyncio.Queue(maxsize=N)}`** —
   capacity 0 means unbounded (asyncio.Queue default, matching JS where a 0 capacity never
   blocks). `channel_send`/`channel_recv` are the async send/recv, blocking like the JS
   promises do.
7. **`is_promise` = `inspect.isawaitable`** — True for coroutines, Futures, and Tasks;
   False for plain values (mirrors the JS `x.then` check).

### Deviations from the JS reference

| # | JS (`omnisys/async.js`) | Python (this package) | Reason |
|---|-------------------------|-----------------------|--------|
| 1 | `race([])` never settles | panics with `PanicError` | Deterministic, debuggable; documented improvement |
| 2 | `any([])` rejects with `AggregateError` | panics on empty | Same spirit, portable exception |
| 3 | Channel object with `send`/`recv`/`size` methods | dict with `'queue'` | asyncio-native; `channel_send`/`channel_recv` are the registry API |
| 4 | `timeout` rejects with `Error("omnisys.async.timeout")` | raises `asyncio.TimeoutError` | Python-native, standard |

---

## 13. Advanced escape: distributed actors (`omnisys_async.actor`)

Closed the "Distributed mode" open question (below) with the v6 advanced escape:
a deterministic actor cluster ported from the JS v5.3 `sim.actor` runtime
(`simulation_engine/runtime.js`, spec §13.5 / §17).

### 13.1 Contract & scope

- Lives in the `actor` submodule — **not** in `OMNISYS_MODULES["async"]` and not
  in `__all__`. The conformance gate (`test_no_unexpected_public_functions`)
  asserts `set(omnisys_async.__all__) == set(OMNISYS_MODULES["async"].functions)`,
  so the escape is exposed as an importable submodule re-exported from the
  package but excluded from the registry surface.
- Declares the `network` capability (mirrors the JS lane: distributed features
  live in a standard-library layer, not the portable grammar).

### 13.2 Design decisions

1. **Runtime object** — `create_runtime()` returns a `Runtime` holding clusters,
   current-cluster, and current-sender state (the JS closure's captured
   variables). Stateless helpers are static: `_dead_letter`, `_is_partitioned`,
   `_node_of_actor_id`, `_lookup_actor_by_id`.
2. **Three API surfaces** — canonical nested `rt.actor.*` / `rt.actor.cluster.*`
   (the JS `sim.actor` / `sim.cluster` namespaces), a flat `rt.sim.*` alias set
   (spawn/send/run/... — the single-dot names the OmniScript parser accepts),
   and the canonical methods directly on the runtime (`rt.cluster_create`,
   `rt.actor_spawn`, ...). Tests cover all three.
3. **Deterministic scheduler** — six phases per step (heartbeat, failure
   detection, supervision, outbox→inbox delivery, inbox→mailbox routing,
   one-message-per-actor processing), all over sorted node/actor order. The
   phases stay in one `_step_cluster` (a faithful port of the monolithic JS
   `_stepCluster`; `# noqa: PLR0912, PLR0915` documents why), kept readable by
   section comments. 100% branch coverage is achieved without splitting.
4. **At-least-once with dead-lettering** — undeliverable envelopes are held in
   the sender's outbox with `attempts` incremented (counted as `redelivered`
   on the second attempt) until delivered or dead-lettered. Dead-letter reasons:
   `unknown-actor`, `actor-gone`, `actor-stopped`, `crash`, `node-removed`,
   `detected-dead`, `restart-limit`.
5. **Supervision** — `fail(node)` crashes a node; the supervisor restarts it up
   to `maxNodeRestarts` (reset to `initialState`, mirroring JS) then removes it
   (`restart-limit`). `fail(node, {"restart": False})` disables auto-restart
   (the node is only removed by heartbeat detection). A crashing behavior
   dead-letters its envelope and restarts up to `maxActorRestarts`.
6. **Membership via heartbeats** — alive nodes ping peers every
   `heartbeatInterval` ticks; peers silent for more than `heartbeatTimeout`
   ticks are removed as `detected-dead`. Partitions are tracked explicitly and
   messages held (not dropped).
7. **Chaos only via explicit API** — partition/heal/fail/restart/remove are
   synchronous, deterministic calls. No sleeps, timers, or randomness anywhere
   in the scheduler.
8. **Panic semantics** — programmer errors (unknown cluster/node/actor, spawn
   on dead node, duplicate spawn, non-callable behavior) raise `PanicError`
   via `omnisys_core.panic`, matching the `omnisys-sim` convention.
9. **100% branch coverage** — every line and branch (including defensive ones)
   is exercised by white-box tests that reach into `_clusters`/internal helpers
   where the public API cannot.

### 13.3 Deviations from the JS reference

| # | JS (`simulation_engine/runtime.js`) | Python (this package) | Reason |
|---|-------------------------------------|-----------------------|--------|
| 1 | `throw new Error(...)` for unknown refs | `PanicError` via `panic` | Monorepo convention |
| 2 | implicit `cluster` arg omitted (current cluster) | explicit `cluster_ref` accepted everywhere (`None` = current) | Typed, testable |
| 3 | `stopActor` not exposed in the JS header list | `cluster_stop_actor` present | Parity with the JS impl body (dead-letters mailbox) |
| 4 | `deadLetters` embedded in stats | the dead-letter *queue* is not embedded; `snapshot` reports only the `deadLetters` count and `deadletters()` exposes the queue | Keeps `statistics` JSON-serializable; the count stays in the snapshot |

---

## 14. Open questions

- **Scheduler model**: work-stealing (Tokio) vs single-loop asyncio — do we need a
  thread-pool escape for CPU-bound tasks?
- **Cancellation propagation**: should `timeout` cancel sibling tasks in `all`/`any`
  scopes (structured concurrency)?
- **Streams**: the JS docstring mentions `Stream`; the registry has no stream functions
  yet — design a `Stream` API in a follow-up.
- ~~Distributed mode~~: **closed** — the actor/cluster escape (§13) answers it; channel
  mapping across nodes remains a possible follow-up.