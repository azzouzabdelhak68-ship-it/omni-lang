# Benchmark Reasoning Log — Project 6.2: Distributed Actor Cluster

**Run Directory**: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
**Model**: DeepSeek V4 Flash Free
**Date**: 2026-08-19

---

## 1. Initial Investigation

### 1.1 Task Understanding
From `TASK.md`:
- Build a distributed message-passing actor cluster with node membership, clustering, failover, and deterministic scheduling
- Use `sim.actor.*` functions (spawn, send, cluster, node, partition, heal, fail, restart, run, members, snapshot)
- Runtime exists in `simulation_engine/runtime.js` and `packages/omnisys-async/`
- Deliverables: BENCHMARK_REASONING.md, source/distributed_actors.omni, tests/test_distributed_actors.py, RESULTS.md

### 1.2 Key Language Facts (from TASK.md)
- `sim.*` functions registered in registry (`sim` module): spawn, send, cluster, node, partition, heal, fail, restart, run, members, snapshot, status, deadletters, statistics
- `OMNISYS.async`: task, delay, all, race, timeout, channel (uses process for check/explain)
- Capability: `uses network` for distributed ops (checker enforces)
- App block calls wrapper functions; never declares capabilities directly
- Map index WRITE = SYNTAX ERROR; use `OMNISYS.collections.map_set`
- Avoid keywords: `box`, `end`, `on`, `error`, `try`, `while`, `global`, `result`

### 1.3 Runtime Analysis
From `simulation_engine/runtime.js`:
- Flat `sim.*` namespace: `sim.spawn(nodeId, name, behavior, initialState)`, `sim.send(target, msg)`, `sim.cluster(name, opts)`, `sim.node(nodeId)`, `sim.partition(a, b)`, `sim.heal(a, b)`, `sim.fail(nodeId, opts)`, `sim.restart(nodeId)`, `sim.remove(nodeId)`, `sim.members(nodeId)`, `sim.deadletters()`, `sim.stats()`, `sim.status()`, `sim.snapshot()`
- Coordinator node auto-created as `<clusterName>.coordinator`
- Deterministic scheduler: nodes sorted by id, actors within node sorted by name, one message per actor per step
- AT-LEAST-ONCE delivery with retry until delivered or dead-lettered
- Heartbeat-based failure detection with configurable intervals
- Node restart policies with max restarts

### 1.4 Example Analysis
From `examples/actors.omni`:
```omni
fn counter_behavior(state: Number, msg: Text) -> Number:
    if msg is "inc": return state + 1 end
    if msg is "dec": return state - 1 end
    return state
end

fn logger_behavior(state: Number, msg: Text) -> Number:
    show msg
    return state
end

when app starts:
    sim.cluster("demo")
    sim.node("n1")
    sim.node("n2")
    counter = sim.spawn("n1", "counter", counter_behavior, 0)
    logger = sim.spawn("n2", "logger", logger_behavior, 0)
    sim.send(counter, "inc")
    sim.send(counter, "inc")
    sim.partition("demo.coordinator", "n2")
    sim.send(logger, "during partition")
    sim.run()
    sim.heal("demo.coordinator", "n2")
    sim.run()
    show join(sim.members("demo.coordinator"), ", ")
    show "done"
end
```

---

## 2. Implementation Plan

### 2.1 Source File: `source/distributed_actors.omni`
Need to implement a comprehensive demo showing:
1. Cluster creation with multiple nodes
2. Actor spawning on different nodes
3. Message passing between actors
4. Network partition and healing
5. Node failure and restart
6. Dead letter handling
7. Membership tracking
8. Statistics and snapshots

### 2.2 Test File: `tests/test_distributed_actors.py`
Need to test:
1. `omni check` / `build` / `verify` pass
2. Cluster membership convergence
3. Partition/heal behavior
4. Crash supervision/restart
5. Message ordering (deterministic scheduling)

---

## 3. Implementation — Step by Step

### 3.1 First Probe: Minimal Cluster
Let me first test the compiler with a minimal example based on the actors.omni example.

[Creating probe...]

---

## 4. Compiler Probes and Experiments

### Probe 1: Basic Cluster (from example)
Testing if the example compiles and runs.

```
omni check examples/actors.omni
```

[Will run after creating the run directory structure]