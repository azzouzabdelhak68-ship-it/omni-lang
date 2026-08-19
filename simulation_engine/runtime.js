"use strict";

/**
 * sim.actor runtime — OmniScript distributed systems layer (v5.3).
 *
 * A self-contained, dependency-free actor runtime for Node.js (CommonJS).
 *
 * Design (spec §13.5 / §17): the core OmniScript grammar stays general;
 * distributed features live in a standard-library layer (`sim.*`). This
 * module implements the `sim.actor.*` runtime that OmniScript actor programs
 * are bridged onto (see README.md for the mapping).
 *
 * Guarantees (all deterministic):
 *  - Message passing is asynchronous, non-blocking, FIFO per mailbox.
 *  - Delivery is AT-LEAST-ONCE: an undeliverable envelope is held (in the
 *    sender's outbox) and retried until it is delivered to a live actor or
 *    dead-lettered. Nothing is silently dropped.
 *  - The scheduler is fully deterministic: nodes are visited in sorted id
 *    order, actors within a node in sorted name order, one message per actor
 *    per scheduling step. Chaos (partitions, node failure) is injected only
 *    through explicit API calls — never through sleeps, timers or randomness.
 *
 * API surface:
 *   sim.actor.spawn(cluster, nodeId, name, behavior, initialState)
 *   sim.actor.send(cluster, target, msg)
 *   sim.actor.sender()                         // actor id processing current msg
 *   sim.actor.receive(behavior, predicate)     // message-handler guard
 *   sim.actor.run(cluster)                     // drain deterministically
 *   sim.actor.step(cluster)                    // one scheduling step
 *   sim.actor.steps(cluster, n)                // exactly n steps
 *   sim.actor.deadletters(cluster)
 *   sim.actor.statistics(cluster)
 *   sim.actor.cluster.create(name, opts)
 *   sim.actor.cluster.addNode(cluster, nodeId)
 *   sim.actor.cluster.partition(cluster, a, b) // network partition a<->b
 *   sim.actor.cluster.heal(cluster, a, b)
 *   sim.actor.cluster.fail(cluster, nodeId, opts)   // node crash
 *   sim.actor.cluster.restart(cluster, nodeId)
 *   sim.actor.cluster.remove(cluster, nodeId)       // permanent removal
 *   sim.actor.cluster.members(cluster, nodeId)      // membership view
 *   sim.actor.cluster.snapshot(cluster)
 *
 * A flat `sim.*` alias set (spawn/send/run/partition/heal/fail/... and the
 * like) is provided for the OmniScript bridge; the OmniScript parser only
 * accepts call names with a single dot, so the .omni source uses these flat
 * names, which resolve to the canonical `sim.actor.*` implementation above.
 *
 * The flat namespace also carries the ECS runtime the platform advertises
 * (v3.4 C-02): sim.entity/sim.system/sim.run(steps)/sim.query/component/get/
 * remove_entity/entities/snapshot, world-less to match the flat call shape.
 */

const VERSION = "5.3.0";

function createRuntime() {
  const clusters = new Map();
  let currentCluster = null;
  let currentSenderId = "";
  let currentSenderNode = null;

  // ------------------------------------------------------------------ utils
  function defaultConfig(opts) {
    const o = opts || {};
    return {
      heartbeatInterval: typeof o.heartbeatInterval === "number" ? o.heartbeatInterval : 3,
      heartbeatTimeout: typeof o.heartbeatTimeout === "number" ? o.heartbeatTimeout : 6,
      maxNodeRestarts: typeof o.maxNodeRestarts === "number" ? o.maxNodeRestarts : 3,
      maxActorRestarts: typeof o.maxActorRestarts === "number" ? o.maxActorRestarts : 3,
      maxSteps: typeof o.maxSteps === "number" ? o.maxSteps : 10000,
    };
  }

  function sortedNodes(cluster) {
    return [...cluster.nodes.values()].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  function clusterOf(ref) {
    if (ref === undefined || ref === null) {
      if (!currentCluster) throw new Error("sim.actor: no current cluster (call cluster.create first)");
      return currentCluster;
    }
    if (typeof ref === "string") {
      const c = clusters.get(ref);
      if (!c) throw new Error(`sim.actor: unknown cluster '${ref}'`);
      return c;
    }
    return ref;
  }

  function coordinatorId(name) {
    return `${name}.coordinator`;
  }

  function nodeOfActorId(cluster, actorId) {
    if (!actorId) return null;
    const slash = actorId.indexOf("/");
    if (slash < 0) return null;
    return cluster.nodes.get(actorId.slice(0, slash)) || null;
  }

  function lookupActorById(cluster, id) {
    const slash = id.indexOf("/");
    if (slash < 0) return null;
    const node = cluster.nodes.get(id.slice(0, slash));
    if (!node || node.removed) return null;
    return node.actors.get(id.slice(slash + 1)) || null;
  }

  function resolveActor(cluster, target) {
    if (target && typeof target === "object" && target.__omniActor) {
      return lookupActorById(cluster, target.id);
    }
    if (typeof target === "string") {
      if (target.indexOf("/") >= 0) return lookupActorById(cluster, target);
      for (const n of sortedNodes(cluster)) {
        if (n.removed) continue;
        const a = n.actors.get(target);
        if (a) return a;
      }
    }
    return null;
  }

  function isPartitioned(cluster, a, b) {
    const pa = cluster.partitions.get(a.id);
    const pb = cluster.partitions.get(b.id);
    return Boolean(pa && pa.has(b.id)) || Boolean(pb && pb.has(a.id));
  }

  function deadLetter(cluster, env, reason) {
    if (env._dead) return;
    env._dead = true;
    env.reason = reason;
    cluster.stats.dead += 1;
    cluster.stats.deadLetters.push({
      seq: env.seq,
      from: env.from,
      to: env.to,
      msg: env.msg,
      reason,
    });
  }

  function removeNode(cluster, nodeId, reason) {
    const node = cluster.nodes.get(nodeId);
    if (!node || node.removed) return;
    node.alive = false;
    node.removed = true;
    for (const a of node.actors.values()) {
      a.alive = false;
      a.stopped = true;
    }
    const prefix = `${nodeId}/`;
    for (const n of cluster.nodes.values()) {
      n.outbox = n.outbox.filter((env) => {
        if (env.to && env.to.startsWith(prefix)) {
          deadLetter(cluster, env, reason);
          return false;
        }
        return true;
      });
      n.inbox = n.inbox.filter((env) => {
        if (env.to && env.to.startsWith(prefix)) {
          deadLetter(cluster, env, reason);
          return false;
        }
        return true;
      });
    }
    for (const a of node.actors.values()) {
      for (const env of a.mailbox) deadLetter(cluster, env, reason);
      a.mailbox = [];
    }
  }

  // ------------------------------------------------------------- cluster ops
  function clusterCreate(name, opts) {
    if (clusters.has(name)) return clusters.get(name);
    const config = defaultConfig(opts);
    const cluster = {
      name,
      config,
      nodes: new Map(),
      partitions: new Map(),
      removed: new Set(),
      seq: 0,
      tick: 0,
      stats: {
        sent: 0,
        delivered: 0,
        redelivered: 0,
        dead: 0,
        crashed: 0,
        restarts: 0,
        failures: 0,
        partitions: 0,
        heals: 0,
        steps: 0,
        deadLetters: [],
      },
    };
    clusters.set(name, cluster);
    clusterAddNode(cluster, coordinatorId(name));
    currentCluster = cluster;
    return cluster;
  }

  function clusterAddNode(clusterRef, nodeId) {
    const cluster = clusterOf(clusterRef);
    if (cluster.nodes.has(nodeId)) return cluster.nodes.get(nodeId);
    const node = {
      id: nodeId,
      cluster,
      alive: true,
      removed: false,
      noRestart: false,
      restarts: 0,
      actors: new Map(),
      outbox: [],
      inbox: [],
      lastHeartbeat: new Map(),
    };
    node.lastHeartbeat.set(nodeId, cluster.tick);
    cluster.nodes.set(nodeId, node);
    return node;
  }

  function clusterPartition(clusterRef, a, b) {
    const cluster = clusterOf(clusterRef);
    const na = cluster.nodes.get(a);
    const nb = cluster.nodes.get(b);
    if (!na || !nb) throw new Error(`sim.actor.partition: unknown node '${a}' or '${b}'`);
    if (!cluster.partitions.has(a)) cluster.partitions.set(a, new Set());
    if (!cluster.partitions.has(b)) cluster.partitions.set(b, new Set());
    cluster.partitions.get(a).add(b);
    cluster.partitions.get(b).add(a);
    cluster.stats.partitions += 1;
  }

  function clusterHeal(clusterRef, a, b) {
    const cluster = clusterOf(clusterRef);
    const na = cluster.nodes.get(a);
    const nb = cluster.nodes.get(b);
    if (!na || !nb) throw new Error(`sim.actor.heal: unknown node '${a}' or '${b}'`);
    if (cluster.partitions.has(a)) cluster.partitions.get(a).delete(b);
    if (cluster.partitions.has(b)) cluster.partitions.get(b).delete(a);
    cluster.stats.heals += 1;
  }

  function clusterFail(clusterRef, nodeId, opts) {
    const cluster = clusterOf(clusterRef);
    const node = cluster.nodes.get(nodeId);
    if (!node) throw new Error(`sim.actor.fail: unknown node '${nodeId}'`);
    if (node.removed) return;
    const o = opts || {};
    node.alive = false;
    node.noRestart = o.restart === false;
    cluster.stats.failures += 1;
  }

  function clusterRestart(clusterRef, nodeId) {
    const cluster = clusterOf(clusterRef);
    const node = cluster.nodes.get(nodeId);
    if (!node || node.removed) return false;
    node.alive = true;
    node.noRestart = false;
    node.restarts += 1;
    cluster.stats.restarts += 1;
    for (const a of node.actors.values()) {
      a.alive = true;
      a.stopped = false;
      a.state = a.initialState;
    }
    for (const n of cluster.nodes.values()) {
      if (n.alive && !n.removed) n.lastHeartbeat.set(nodeId, cluster.tick);
    }
    node.lastHeartbeat.set(nodeId, cluster.tick);
    return true;
  }

  function clusterRemove(clusterRef, nodeId) {
    const cluster = clusterOf(clusterRef);
    removeNode(cluster, nodeId, "node-removed");
  }

  function clusterStopActor(clusterRef, nodeId, name) {
    const cluster = clusterOf(clusterRef);
    const node = cluster.nodes.get(nodeId);
    if (!node) throw new Error(`sim.actor.stopActor: unknown node '${nodeId}'`);
    const actor = node.actors.get(name);
    if (!actor) throw new Error(`sim.actor.stopActor: unknown actor '${name}' on '${nodeId}'`);
    actor.alive = false;
    actor.stopped = true;
    for (const env of actor.mailbox) deadLetter(cluster, env, "actor-stopped");
    actor.mailbox = [];
  }

  function clusterMembers(clusterRef, nodeId) {
    const cluster = clusterOf(clusterRef);
    const node = cluster.nodes.get(nodeId);
    if (!node || !node.alive || node.removed) return [];
    const out = [];
    for (const m of sortedNodes(cluster)) {
      if (!m.alive || m.removed) continue;
      if (m.id === nodeId || !isPartitioned(cluster, node, m)) out.push(m.id);
    }
    return out;
  }

  // --------------------------------------------------------------- scheduler
  function stepCluster(cluster) {
    const config = cluster.config;
    cluster.tick += 1;
    cluster.stats.steps += 1;
    let work = false;

    // 1. heartbeats (every interval, alive nodes ping their peers)
    if (cluster.tick % config.heartbeatInterval === 0) {
      const alive = sortedNodes(cluster).filter((n) => n.alive && !n.removed);
      for (const n of alive) {
        for (const m of alive) n.lastHeartbeat.set(m.id, cluster.tick);
      }
    }

    // 2. failure detection — peers we have not heard from are removed
    for (const n of sortedNodes(cluster)) {
      if (!n.alive || n.removed) continue;
      for (const p of cluster.nodes.values()) {
        if (p.id === n.id || p.alive || p.removed) continue;
        const last = n.lastHeartbeat.get(p.id);
        const since = last === undefined ? cluster.tick : cluster.tick - last;
        if (since > config.heartbeatTimeout && !cluster.removed.has(p.id)) {
          cluster.stats.failures += 1;
          removeNode(cluster, p.id, "detected-dead");
          work = true;
        }
      }
    }

    // 3. supervision — restart crashed nodes; remove unrecoverable ones
    for (const p of cluster.nodes.values()) {
      if (p.alive || p.removed) continue;
      if (p.noRestart) continue; // wait for heartbeat detection to remove it
      if (p.restarts < config.maxNodeRestarts) {
        clusterRestart(cluster, p.id);
        work = true;
      } else {
        removeNode(cluster, p.id, "restart-limit");
        work = true;
      }
    }

    // 4. deliver outboxes -> target node inboxes (held while partitioned/dead)
    for (const n of sortedNodes(cluster)) {
      if (!n.alive || n.removed) continue;
      const keep = [];
      for (const env of n.outbox) {
        if (env._dead) continue;
        const actor = resolveActor(cluster, env.to);
        if (!actor) {
          deadLetter(cluster, env, "actor-gone");
          work = true;
          continue;
        }
        const tn = actor.node;
        if (!tn.alive || tn.removed) {
          env.attempts += 1;
          if (env.attempts > 1) cluster.stats.redelivered += 1;
          keep.push(env);
          continue;
        }
        if (isPartitioned(cluster, n, tn)) {
          env.attempts += 1;
          if (env.attempts > 1) cluster.stats.redelivered += 1;
          keep.push(env);
          continue;
        }
        env.attempts += 1;
        if (env.attempts > 1) cluster.stats.redelivered += 1;
        tn.inbox.push(env);
        work = true;
      }
      n.outbox = keep;
    }

    // 5. inboxes -> actor mailboxes
    for (const n of sortedNodes(cluster)) {
      if (!n.alive || n.removed) continue;
      const inbox = n.inbox;
      n.inbox = [];
      for (const env of inbox) {
        if (env._dead) continue;
        const actor = resolveActor(cluster, env.to);
        if (!actor || !actor.alive || actor.stopped) {
          deadLetter(cluster, env, "actor-gone");
          work = true;
        } else {
          actor.mailbox.push(env);
          work = true;
        }
      }
    }

    // 6. process one message per actor (sorted node, sorted name, FIFO mailbox)
    for (const n of sortedNodes(cluster)) {
      if (!n.alive || n.removed) continue;
      for (const name of [...n.actors.keys()].sort()) {
        const actor = n.actors.get(name);
        if (!actor.alive || actor.stopped) continue;
        const env = actor.mailbox.shift();
        if (!env) continue;
        work = true;
        let next;
        let crashed = false;
        try {
          currentSenderId = env.from;
          currentSenderNode = nodeOfActorId(cluster, env.from);
          next = actor.behavior(actor.state, env.msg, {
            self: actor.id,
            node: actor.node.id,
            sender: env.from,
          });
        } catch (err) {
          crashed = true;
          actor.crashes += 1;
          cluster.stats.crashed += 1;
          deadLetter(cluster, env, "crash");
          if (actor.restarts < config.maxActorRestarts) {
            actor.restarts += 1;
            cluster.stats.restarts += 1;
            actor.state = actor.initialState;
            work = true;
          } else {
            actor.alive = false;
            actor.stopped = true;
            for (const m of actor.mailbox) deadLetter(cluster, m, "actor-stopped");
            actor.mailbox = [];
          }
        } finally {
          currentSenderId = "";
          currentSenderNode = null;
        }
        if (!crashed) {
          actor.state = next === undefined ? actor.state : next;
          actor.processed += 1;
          cluster.stats.delivered += 1;
        }
      }
    }

    return work;
  }

  function runCluster(clusterRef) {
    const cluster = clusterOf(clusterRef);
    const max = cluster.config.maxSteps;
    for (let i = 0; i < max; i += 1) {
      if (!stepCluster(cluster)) break;
    }
    return cluster.stats;
  }

  function stepsCluster(clusterRef, n) {
    const cluster = clusterOf(clusterRef);
    for (let i = 0; i < n; i += 1) stepCluster(cluster);
    return cluster.stats;
  }

  // ------------------------------------------------------------------- actors
  function actorSpawn(clusterRef, nodeId, name, behavior, initialState) {
    const cluster = clusterOf(clusterRef);
    const node = cluster.nodes.get(nodeId);
    if (!node) throw new Error(`sim.actor.spawn: unknown node '${nodeId}' in cluster '${cluster.name}'`);
    if (!node.alive) throw new Error(`sim.actor.spawn: node '${nodeId}' is not alive`);
    if (node.actors.has(name)) {
      throw new Error(`sim.actor.spawn: actor '${name}' already exists on node '${nodeId}'`);
    }
    if (typeof behavior !== "function") {
      throw new Error(`sim.actor.spawn: behavior for '${name}' is not a function`);
    }
    const actor = {
      node,
      name,
      id: `${nodeId}/${name}`,
      behavior,
      initialState,
      state: initialState,
      mailbox: [],
      alive: true,
      stopped: false,
      restarts: 0,
      crashes: 0,
      processed: 0,
    };
    node.actors.set(name, actor);
    return { __omniActor: true, id: actor.id, node: nodeId, name };
  }

  function actorSend(clusterRef, target, msg) {
    const cluster = clusterOf(clusterRef);
    const from = currentSenderId || "";
    const sourceNode = currentSenderNode || cluster.nodes.get(coordinatorId(cluster.name));
    const actor = resolveActor(cluster, target);
    const env = {
      seq: (cluster.seq += 1),
      from,
      to: actor ? actor.id : null,
      msg,
      attempts: 0,
    };
    if (!actor) {
      deadLetter(cluster, env, "unknown-actor");
      return env.seq;
    }
    cluster.stats.sent += 1;
    sourceNode.outbox.push(env);
    return env.seq;
  }

  function actorSender() {
    return currentSenderId;
  }

  function actorReceive(behavior, predicate) {
    const wrapped = function wrappedBehavior(state, msg, ctx) {
      if (typeof predicate === "function" && !predicate(msg, ctx)) {
        wrapped.dropped += 1;
        return state;
      }
      return behavior(state, msg, ctx);
    };
    wrapped.dropped = 0;
    return wrapped;
  }

  // ------------------------------------------------------------------ inspect
  function clusterSnapshot(clusterRef) {
    const cluster = clusterOf(clusterRef);
    return {
      name: cluster.name,
      tick: cluster.tick,
      partitions: [...cluster.partitions.entries()].map(([a, set]) => [a, [...set].sort()]),
      stats: {
        sent: cluster.stats.sent,
        delivered: cluster.stats.delivered,
        redelivered: cluster.stats.redelivered,
        dead: cluster.stats.dead,
        crashed: cluster.stats.crashed,
        restarts: cluster.stats.restarts,
        failures: cluster.stats.failures,
        partitions: cluster.stats.partitions,
        heals: cluster.stats.heals,
        steps: cluster.stats.steps,
        deadLetters: cluster.stats.deadLetters.length,
      },
      nodes: sortedNodes(cluster).map((n) => ({
        id: n.id,
        alive: n.alive,
        removed: n.removed,
        restarts: n.restarts,
        members: clusterMembers(cluster, n.id),
        actors: [...n.actors.keys()].sort().map((name) => {
          const a = n.actors.get(name);
          return {
            name,
            state: a.state,
            alive: a.alive,
            stopped: a.stopped,
            processed: a.processed,
            restarts: a.restarts,
            crashes: a.crashes,
            mailbox: a.mailbox.map((e) => ({ from: e.from, to: e.to, msg: e.msg })),
          };
        }),
      })),
    };
  }

  function clusterStatus(clusterRef) {
    const cluster = clusterOf(clusterRef);
    const out = {};
    for (const n of sortedNodes(cluster)) {
      out[n.id] = {
        alive: n.alive,
        removed: n.removed,
        restarts: n.restarts,
        partitions: cluster.partitions.get(n.id) ? [...cluster.partitions.get(n.id)].sort() : [],
        lastHeartbeat: [...n.lastHeartbeat.entries()].map(([k, v]) => [k, v]),
      };
    }
    return out;
  }

  function actorDeadletters(clusterRef) {
    return clusterOf(clusterRef).stats.deadLetters.slice();
  }

  function actorStatistics(clusterRef) {
    const c = clusterOf(clusterRef);
    return {
      sent: c.stats.sent,
      delivered: c.stats.delivered,
      redelivered: c.stats.redelivered,
      dead: c.stats.dead,
      crashed: c.stats.crashed,
      restarts: c.stats.restarts,
      failures: c.stats.failures,
      partitions: c.stats.partitions,
      heals: c.stats.heals,
      steps: c.stats.steps,
    };
  }

  // ------------------------------------------------------------- ECS runtime
  // Flat `sim.*` ECS bridge (v3.4 C-02 parity with `omnisys.sim`). The
  // platform advertises an ECS API (world/entity/component/system/query), so
  // the flat namespace used by OmniScript source must provide it — previously
  // only the actor aliases shipped and consumers had to inject their own
  // runtime. State is implicit (no explicit world handle) to match the flat
  // single-dot call shape the parser accepts:
  //   sim.entity(name, [components])        sim.system(name, fn, [components])
  //   sim.run(steps)                        sim.query(component) -> [names]
  // plus the registry `omnisys.sim` surface in world-less form.
  function createEcs() {
    const state = { entities: {}, order: [], systems: [], step: 0 };
    return {
      entity(name, comps) {
        if (!Object.prototype.hasOwnProperty.call(state.entities, name)) {
          const components = {};
          for (const c of (comps || [])) components[String(c)] = null;
          state.entities[name] = components;
          state.order.push(name);
        }
        return name;
      },
      component(name, component, value) {
        if (!Object.prototype.hasOwnProperty.call(state.entities, name)) {
          state.entities[name] = {};
          state.order.push(name);
        }
        state.entities[name][String(component)] = value;
        return name;
      },
      get(name, component) {
        const entity = state.entities[name];
        if (!entity) throw new Error("sim.get: unknown entity " + name);
        return entity[String(component)];
      },
      system(name, fn, comps) {
        state.systems.push({ name, fn, comps: (comps || []).map(String) });
        return name;
      },
      run(steps) {
        const n = Math.max(0, steps | 0);
        for (let i = 0; i < n; i += 1) {
          for (const sys of state.systems) sys.fn(state);
          state.step += 1;
        }
        return steps;
      },
      query(component) {
        return state.order.filter((name) =>
          Object.prototype.hasOwnProperty.call(state.entities[name], String(component))
        );
      },
      remove_entity(name) {
        delete state.entities[name];
        state.order = state.order.filter((x) => x !== name);
        return name;
      },
      entities() {
        return state.order.slice();
      },
      snapshot() {
        return {
          tag: "world",
          step: state.step,
          systems: state.systems.map((s) => s.name),
          entities: JSON.parse(JSON.stringify(state.entities)),
          order: state.order.slice(),
        };
      },
    };
  }

  // ------------------------------------------------------------ public object
  const cluster = {
    create: clusterCreate,
    addNode: clusterAddNode,
    partition: clusterPartition,
    heal: clusterHeal,
    fail: clusterFail,
    restart: clusterRestart,
    remove: clusterRemove,
    stopActor: clusterStopActor,
    members: clusterMembers,
    snapshot: clusterSnapshot,
    status: clusterStatus,
    steps: stepsCluster,
    run: runCluster,
  };

  const actor = {
    spawn: actorSpawn,
    send: actorSend,
    sender: actorSender,
    receive: actorReceive,
    run: runCluster,
    step: stepCluster,
    steps: stepsCluster,
    deadletters: actorDeadletters,
    statistics: actorStatistics,
    cluster,
  };

  // Flat `sim.*` aliases — the OmniScript bridge. The OmniScript parser only
  // accepts call names with a single dot (`sim.spawn`, `sim.partition`, ...),
  // so the .omni source uses these; they all delegate to `sim.actor.*` and the
  // flat ECS runtime above.
  const ecs = createEcs();
  const sim = {
    actor,
    version: VERSION,
    spawn: (nodeId, name, behavior, initialState) => actorSpawn(undefined, nodeId, name, behavior, initialState),
    send: (target, msg) => actorSend(undefined, target, msg),
    sender: () => actorSender(),
    run: (steps) => (typeof steps === "number" ? ecs.run(steps) : runCluster(undefined)),
    step: () => stepCluster(undefined),
    steps: (n) => stepsCluster(undefined, n),
    cluster: (name, opts) => clusterCreate(name, opts),
    node: (nodeId) => clusterAddNode(undefined, nodeId),
    partition: (a, b) => clusterPartition(undefined, a, b),
    heal: (a, b) => clusterHeal(undefined, a, b),
    fail: (nodeId, opts) => clusterFail(undefined, nodeId, opts),
    restart: (nodeId) => clusterRestart(undefined, nodeId),
    remove: (nodeId) => clusterRemove(undefined, nodeId),
    stop_actor: (nodeId, name) => clusterStopActor(undefined, nodeId, name),
    members: (nodeId) => clusterMembers(undefined, nodeId),
    deadletters: () => actorDeadletters(undefined),
    stats: () => actorStatistics(undefined),
    status: () => (currentCluster ? clusterStatus(undefined) : {}),
    // Flat ECS (see createEcs): world-less entity/component/system/query.
    entity: ecs.entity,
    component: ecs.component,
    get: ecs.get,
    system: ecs.system,
    query: ecs.query,
    remove_entity: ecs.remove_entity,
    entities: ecs.entities,
    snapshot: ecs.snapshot,
  };

  return { sim, version: VERSION };
}

module.exports = { createRuntime, VERSION };
