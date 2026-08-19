# OMNISYS.async

**OMNISYS.async** is the async/concurrency module of the OMNISYS platform:
Task, Future, Channel, Select-style combinators, and timeouts. The Python
lane is built on `asyncio`.

## Python lane

```python
import omnisys_async
from omnisys_async import all, channel, channel_send, channel_recv, timeout

task = omnisys_async.task(lambda: 42)
result = await all([task, omnisys_async.delay(1)])
ch = channel(4)
await channel_send(ch, 'value')
value = await channel_recv(ch)
```

This package is the Python reference implementation of the JS runtime in
`omnisys/async.js`. Function names and semantics match the registry contract
in `omni_compiler/omnisys_registry.py`; tasks are awaitables, the channel is a
bounded FIFO backed by `asyncio.Queue`.

## Advanced escape: distributed actors (`omnisys_async.actor`)

The `actor` submodule is the **advanced async escape** (v6): a self-contained,
dependency-free, fully deterministic actor cluster ported from the JS v5.3
`sim.actor` runtime (`simulation_engine/runtime.js`).

- It is **NOT** part of the portable registry contract
  (`OMNISYS_MODULES["async"]`) — it is an escape that declares the `network`
  capability, mirroring how the JS lane's `sim.actor` bridge sits outside the
  portable `omnisys/async.js` module.
- **Guarantees (all deterministic — no sleeps, timers, or randomness):**
  - asynchronous, non-blocking, FIFO-per-mailbox message passing;
  - **at-least-once** delivery: an undeliverable envelope is held in the
    sender's outbox and retried until delivered or dead-lettered;
  - deterministic scheduler: nodes in sorted id order, actors within a node in
    sorted name order, one message per actor per scheduling step;
  - chaos (partitions, node failure, restart) is injected only through explicit
    API calls;
  - supervisors restart crashed nodes/actors (bounded by
    `maxNodeRestarts`/`maxActorRestarts`) and dead-letter what cannot recover.

```python
from omnisys_async import actor

rt = actor.create_runtime()
sim = rt.sim  # flat aliases (single-dot names used by .omni)
c = sim.cluster('demo')
sim.node('n1')
sim.spawn('n1', 'counter', lambda state, msg, ctx: state + msg, 0)
sim.send('n1/counter', 1)
sim.run()
print(sim.statistics())  # {'delivered': 1, ...}
snap = rt.actor.cluster.snapshot(c)
counter = next(a for node in snap['nodes'] for a in node['actors'] if a['name'] == 'counter')
print(counter['state'])  # 1
```

Canonical nested API: `rt.actor.spawn/send/receive/run/step/steps/sender/
deadletters/statistics` plus `rt.actor.cluster.create/add_node/partition/heal/
fail/restart/remove/stop_actor/members/snapshot/status` (JS-shaped `sim.actor`
/`sim.cluster` namespaces). `rt.sim` is the flat single-dot facade
(`sim.cluster/node/spawn/send/run/step/steps/sender/receive/statistics/
deadletters/status`), and every method also exists on the runtime directly
(`rt.cluster_create`, `rt.actor_spawn`, ...). Behaviors have the
signature `behavior(state, msg, ctx) -> next_state` with
`ctx = {"self", "node", "sender"}`; returning `None` leaves state unchanged.

See [RESEARCH.md](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.

## Dependencies

- `omnisys_core` (for `panic`)

## Docs

- [RESEARCH.md](RESEARCH.md) — research gate + design decisions
- [tests/](tests/) — unit, property, and registry-conformance tests