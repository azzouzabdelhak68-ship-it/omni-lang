# `simulation_engine` — OmniScript Distributed Systems Runtime (v5.3)

Self-contained, dependency-free Node.js (CommonJS) runtime implementing the
actor model, message passing, clustering, and fault tolerance for OmniScript.
It follows the spec's established philosophy (§13.5, §17): distributed
features are a **standard-library layer (`sim.*`)**, not grammar keywords.

- `runtime.js` — the runtime (the only file you need; ~100% self-contained).
- `README.md` — this document.

## Guarantees

- **Asynchronous, non-blocking** `send`: enqueues and returns immediately.
- **FIFO per mailbox**: one actor processes messages in order, one message at
  a time (a message-handler loop — the behavior IS the receive handler).
- **At-least-once delivery**: an envelope that cannot yet be delivered (target
  node dead or network-partitioned) is held in the sender's outbox and retried
  until it is delivered to a live actor or dead-lettered. **Nothing is
  silently dropped.**
- **Deterministic**: nodes are visited in sorted id order, actors within a
  node in sorted name order, one message per actor per scheduling step. There
  are no timers, sleeps, or random sources. Replaying the same sequence of
  operations produces bit-identical state (`sim.actor.cluster.snapshot`).

## API surface (canonical `sim.actor.*`)

```
sim.actor.spawn(cluster, nodeId, name, behavior, initialState) -> actorRef
sim.actor.send(cluster, target, msg)                    -> seq (Number)
sim.actor.sender()                                      -> sender actor id
sim.actor.receive(behavior, predicate?)                 -> wrapped behavior
sim.actor.run(cluster)      sim.actor.step(cluster)
sim.actor.steps(cluster, n)                             -> stats
sim.actor.deadletters(cluster)                          -> [ {seq,from,to,msg,reason} ]
sim.actor.statistics(cluster)                           -> counters

sim.actor.cluster.create(name, opts?)                   -> cluster (sets current)
sim.actor.cluster.addNode(cluster, nodeId)              -> node
sim.actor.cluster.partition(cluster, a, b)              // network partition a<->b
sim.actor.cluster.heal(cluster, a, b)                   // heal a<->b (redeliver held)
sim.actor.cluster.fail(cluster, nodeId, {restart?})     // crash node (supervisor restarts)
sim.actor.cluster.restart(cluster, nodeId)              // manual restart
sim.actor.cluster.remove(cluster, nodeId)               // permanent removal + dead-letter
sim.actor.cluster.stopActor(cluster, nodeId, name)      // stop one actor + dead-letter
sim.actor.cluster.members(cluster, nodeId)              -> [nodeIds]  (membership view)
sim.actor.cluster.snapshot(cluster)                     -> full state
```

Options (`cluster.create`): `heartbeatInterval` (3), `heartbeatTimeout` (6),
`maxNodeRestarts` (3), `maxActorRestarts` (3), `maxSteps` (10000).

`behavior(state, msg, ctx) -> newState` — pure-ish state transformer;
`ctx` = `{ self, node, sender }`. A returned `undefined` keeps the state.
A throwing behavior is a crash: the supervisor restarts the actor with its
initial state (up to `maxActorRestarts`), then permanently stops it and
dead-letters its mailbox.

## Clustering, membership, failure detection

- Every cluster gets a `coordinator` node (`<cluster>.coordinator`) that hosts
  the OmniScript entry point's sends. Worker nodes are added with `addNode`.
- Heartbeats: every `heartbeatInterval` ticks alive nodes ping all peers.
  `members(nodeId)` returns the sorted list of nodes visible to `nodeId`
  (alive, not removed, not partitioned from it).
- A node that is dead and has not been heard from for `heartbeatTimeout` ticks
  is **detected** by its peers and removed from membership (dead-letters its
  pending messages).
- `fail` crashes a node; the supervisor either **restarts** it (actors are
  resurrected with initial state; held/in-flight messages are redelivered) or,
  past `maxNodeRestarts` / with `{restart:false}`, leaves it for heartbeat
  detection to remove.

## Deterministic chaos testing

Chaos is **injected through explicit API calls at explicit points**, never
through sleeps or randomness:

```
cluster.partition(a, b)   // messages a<->b are held in outboxes, not delivered
cluster.heal(a, b)        // held messages are redelivered (or dead-lettered
                          //   deterministically if the target is gone)
cluster.fail(node)        // node crash -> supervisor restart, no message loss
cluster.restart(node)     // manual restart
cluster.remove(node)      // permanent removal -> pending messages dead-lettered
cluster.stopActor(...)    // kill one actor -> its pending messages dead-letter
```

Run with `sim.actor.run(cluster)` (drain to quiescence) or
`sim.actor.steps(cluster, n)` (advance exactly n ticks for heartbeat-detection
scenarios). Tests replay identical scenarios and assert identical snapshots.

## OmniScript bridge (`.omni` -> runtime calls)

The OmniScript **parser only accepts call names with a single dot**, so the
`.omni` source uses flat `sim.*` aliases that delegate to the canonical
`sim.actor.*` implementation above. The mapping:

| OmniScript call                 | runtime equivalent                     |
|---------------------------------|----------------------------------------|
| `sim.cluster(name)`             | `sim.actor.cluster.create(name)`       |
| `sim.node(id)`                  | `sim.actor.cluster.addNode(c, id)`     |
| `sim.spawn(node, name, beh, s)` | `sim.actor.spawn(c, node, name, beh, s)` |
| `sim.send(target, msg)`         | `sim.actor.send(c, target, msg)`       |
| `sim.sender()`                  | `sim.actor.sender()`                   |
| `sim.run()` / `sim.step()`      | `sim.actor.run(c)` / `sim.actor.step(c)` |
| `sim.partition(a, b)`           | `sim.actor.cluster.partition(c, a, b)` |
| `sim.heal(a, b)`                | `sim.actor.cluster.heal(c, a, b)`      |
| `sim.fail(node)`                | `sim.actor.cluster.fail(c, node)`      |
| `sim.restart(node)`             | `sim.actor.cluster.restart(c, node)`   |
| `sim.remove(node)`              | `sim.actor.cluster.remove(c, node)`    |
| `sim.members(node)`             | `sim.actor.cluster.members(c, node)`   |
| `sim.deadletters()`             | `sim.actor.deadletters(c)`             |

An actor behavior is just an OmniScript function
`fn beh(state, msg) -> State` — it IS the receive handler. The runtime calls
it as `behavior(state, msg, ctx)`; extra declared params (like `ctx`) are
ignored if not declared, and behaviors can reply with
`sim.send(sim.sender(), msg)`.

See `examples/actors.omni` (message passing, partition/heal) and
`examples/chaos.omni` (node failure, supervision, at-least-once).

## Running

```
node scripts/run-actors.js <emitted.html>     # run an emitted actor program
python scripts/run-actors.py examples/actors.omni   # compile + run end-to-end
```

## Limitations (honest)

- Single-process simulation: "nodes" share one event loop; the runtime models
  the distributed semantics (partitions, failure detection, redelivery), not
  real process isolation. It is deterministic *by design*, so chaos tests are
  reproducible without a real network.
- At-least-once is delivered without a separate ack/reply handshake: a message
  is retried until delivered or dead-lettered. Duplicate delivery to a live
  handler is not generated (handlers that crash on a message get that message
  dead-lettered rather than retried forever).
- The OmniScript bridge is limited to single-dot `sim.*` names by the core
  parser (see above).
- `run()` stops at quiescence or `maxSteps`; a behavior that endlessly re-sends
  to itself will hit the step budget.