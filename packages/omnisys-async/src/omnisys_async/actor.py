"""OMNISYS.async.actor — deterministic distributed actor runtime (escape).

The "advanced" escape for :mod:`omnisys_async`: distributed actors and
clustering. This submodule ports the v5.3 ``sim.actor`` runtime from
``simulation_engine/runtime.js`` to Python. It is *not* part of the OMNISYS
registry contract — the ten registry functions live in the package root — and
is importable as ``omnisys_async.actor``.

Guarantees (mirroring the JS runtime, all deterministic):

- Message passing is asynchronous, non-blocking, FIFO per mailbox.
- Delivery is AT-LEAST-ONCE: an undeliverable envelope is held in the sender's
  outbox and retried until it is delivered to a live actor or dead-lettered.
  Nothing is silently dropped.
- The scheduler is fully deterministic: nodes are visited in sorted id order,
  actors within a node in sorted name order, one message per actor per
  scheduling step. Chaos (partitions, node failure) is injected only through
  explicit API calls.

``ActorRuntime`` mirrors the ``sim.*``/``sim.actor.*`` surface. Flat aliases
(``spawn``, ``send``, ``run``, ...) operate on the current cluster, set by
``cluster_create``; namespaced methods take an optional cluster reference
(the cluster dict, a cluster name, or ``None`` for the current cluster).
"""

from collections.abc import Callable
from typing import Any, cast

from omnisys_core import panic

VERSION = '5.3.0'

Behavior = Callable[[Any, Any, dict[str, Any]], Any]
Predicate = Callable[[Any, dict[str, Any]], bool]

_DEFAULT_HEARTBEAT_INTERVAL = 3
_DEFAULT_HEARTBEAT_TIMEOUT = 6
_DEFAULT_MAX_NODE_RESTARTS = 3
_DEFAULT_MAX_ACTOR_RESTARTS = 3
_DEFAULT_MAX_STEPS = 10000
_FIRST_ATTEMPT = 1


def _default_config(opts: dict[str, Any] | None) -> dict[str, Any]:
    """Build the cluster config, honouring numeric ``opts`` overrides."""

    def number(key: str, default: int) -> int:
        value = (opts or {}).get(key)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return int(value)
        return default

    return {
        'heartbeat_interval': number('heartbeat_interval', _DEFAULT_HEARTBEAT_INTERVAL),
        'heartbeat_timeout': number('heartbeat_timeout', _DEFAULT_HEARTBEAT_TIMEOUT),
        'max_node_restarts': number('max_node_restarts', _DEFAULT_MAX_NODE_RESTARTS),
        'max_actor_restarts': number('max_actor_restarts', _DEFAULT_MAX_ACTOR_RESTARTS),
        'max_steps': number('max_steps', _DEFAULT_MAX_STEPS),
    }


class ReceiveBehavior:
    """A behavior guarded by a message predicate (mirrors ``sim.actor.receive``).

    Messages failing ``predicate`` are dropped (counted in ``dropped``) and the
    state is left unchanged.
    """

    def __init__(self, behavior: Behavior, predicate: Predicate | None = None) -> None:
        """Wrap ``behavior`` with an optional message ``predicate``."""
        self._behavior = behavior
        self._predicate = predicate
        self.dropped = 0

    def __call__(self, state: Any, msg: Any, ctx: dict[str, Any]) -> Any:
        """Forward to the wrapped behavior, dropping messages failing the guard."""
        if self._predicate is not None and not self._predicate(msg, ctx):
            self.dropped += 1
            return state
        return self._behavior(state, msg, ctx)


class ActorRuntime:
    """A deterministic actor/cluster runtime (mirrors ``createRuntime().sim``)."""

    def __init__(self) -> None:
        """Create a fresh runtime with no clusters."""
        self._clusters: dict[str, dict[str, Any]] = {}
        self._current: dict[str, Any] | None = None
        self._sender_id = ''
        self._sender_node: dict[str, Any] | None = None

    # --------------------------------------------------------------- cluster

    def cluster_create(self, name: str, opts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a cluster; returns the existing cluster if ``name`` is taken."""
        existing = self._clusters.get(name)
        if existing is not None:
            return existing
        cluster: dict[str, Any] = {
            'name': name,
            'config': _default_config(opts),
            'nodes': {},
            'partitions': {},
            'removed': set(),
            'seq': 0,
            'tick': 0,
            'stats': {
                'sent': 0,
                'delivered': 0,
                'redelivered': 0,
                'dead': 0,
                'crashed': 0,
                'restarts': 0,
                'failures': 0,
                'partitions': 0,
                'heals': 0,
                'steps': 0,
                'dead_letters': [],
            },
        }
        self._clusters[name] = cluster
        self._cluster_add_node(cluster, self._coordinator_id(name))
        self._current = cluster
        return cluster

    def cluster_add_node(self, ref: dict[str, Any] | str | None, node_id: str) -> dict[str, Any]:
        """Add a live node to the cluster; returns the existing node if present."""
        cluster = self._cluster_of(ref)
        return self._cluster_add_node(cluster, node_id)

    def cluster_partition(self, ref: dict[str, Any] | str | None, a: str, b: str) -> None:
        """Partition two nodes from each other (bi-directional)."""
        cluster = self._cluster_of(ref)
        if a not in cluster['nodes'] or b not in cluster['nodes']:
            panic(f"sim.actor.partition: unknown node '{a}' or '{b}'")
        cluster['partitions'].setdefault(a, set()).add(b)
        cluster['partitions'].setdefault(b, set()).add(a)
        cluster['stats']['partitions'] += 1

    def cluster_heal(self, ref: dict[str, Any] | str | None, a: str, b: str) -> None:
        """Heal a partition between two nodes."""
        cluster = self._cluster_of(ref)
        if a not in cluster['nodes'] or b not in cluster['nodes']:
            panic(f"sim.actor.heal: unknown node '{a}' or '{b}'")
        if a in cluster['partitions']:
            cluster['partitions'][a].discard(b)
        if b in cluster['partitions']:
            cluster['partitions'][b].discard(a)
        cluster['stats']['heals'] += 1

    def cluster_fail(
        self,
        ref: dict[str, Any] | str | None,
        node_id: str,
        opts: dict[str, Any] | None = None,
    ) -> None:
        """Crash a node; ``{'restart': False}`` disables supervision restart."""
        cluster = self._cluster_of(ref)
        node = cluster['nodes'].get(node_id)
        if node is None:
            panic(f"sim.actor.fail: unknown node '{node_id}'")
        if node['removed']:
            return
        o = opts or {}
        node['alive'] = False
        node['no_restart'] = o.get('restart') is False
        cluster['stats']['failures'] += 1

    def cluster_restart(self, ref: dict[str, Any] | str | None, node_id: str) -> bool:
        """Restart a crashed node, resetting its actors; False when impossible."""
        cluster = self._cluster_of(ref)
        node = cluster['nodes'].get(node_id)
        if node is None or node['removed']:
            return False
        node['alive'] = True
        node['no_restart'] = False
        node['restarts'] += 1
        cluster['stats']['restarts'] += 1
        for actor in node['actors'].values():
            actor['alive'] = True
            actor['stopped'] = False
            actor['state'] = actor['initial_state']
        for other in cluster['nodes'].values():
            if other['alive'] and not other['removed']:
                other['last_heartbeat'][node_id] = cluster['tick']
        node['last_heartbeat'][node_id] = cluster['tick']
        return True

    def cluster_remove(self, ref: dict[str, Any] | str | None, node_id: str) -> None:
        """Permanently remove a node, dead-lettering every envelope to it."""
        self._remove_node(self._cluster_of(ref), node_id, 'node-removed')

    def cluster_stop_actor(self, ref: dict[str, Any] | str | None, node_id: str, name: str) -> None:
        """Stop an actor, dead-lettering its queued messages."""
        cluster = self._cluster_of(ref)
        node = cluster['nodes'].get(node_id)
        if node is None:
            panic(f"sim.actor.stopActor: unknown node '{node_id}'")
        actor = node['actors'].get(name)
        if actor is None:
            panic(f"sim.actor.stopActor: unknown actor '{name}' on '{node_id}'")
        actor['alive'] = False
        actor['stopped'] = True
        for env in actor['mailbox']:
            self._dead_letter(cluster, env, 'actor-stopped')
        actor['mailbox'] = []

    def cluster_members(self, ref: dict[str, Any] | str | None, node_id: str) -> list[str]:
        """Return the ids of nodes this node can reach (itself always included)."""
        cluster = self._cluster_of(ref)
        node = cluster['nodes'].get(node_id)
        if node is None or not node['alive'] or node['removed']:
            return []
        out: list[str] = []
        for member in self._sorted_nodes(cluster):
            if not member['alive'] or member['removed']:
                continue
            if member['id'] == node_id or not self._is_partitioned(cluster, node, member):
                out.append(member['id'])
        return out

    def cluster_snapshot(self, ref: dict[str, Any] | str | None) -> dict[str, Any]:
        """Return a deep snapshot of the cluster (mirrors ``clusterSnapshot``)."""
        cluster = self._cluster_of(ref)
        stats = cluster['stats']
        return {
            'name': cluster['name'],
            'tick': cluster['tick'],
            'partitions': [[a, sorted(p)] for a, p in sorted(cluster['partitions'].items())],
            'stats': {
                'sent': stats['sent'],
                'delivered': stats['delivered'],
                'redelivered': stats['redelivered'],
                'dead': stats['dead'],
                'crashed': stats['crashed'],
                'restarts': stats['restarts'],
                'failures': stats['failures'],
                'partitions': stats['partitions'],
                'heals': stats['heals'],
                'steps': stats['steps'],
                'deadLetters': len(stats['dead_letters']),
            },
            'nodes': [
                {
                    'id': node['id'],
                    'alive': node['alive'],
                    'removed': node['removed'],
                    'restarts': node['restarts'],
                    'members': self.cluster_members(cluster, node['id']),
                    'actors': [
                        {
                            'name': name,
                            'state': actor['state'],
                            'alive': actor['alive'],
                            'stopped': actor['stopped'],
                            'processed': actor['processed'],
                            'restarts': actor['restarts'],
                            'crashes': actor['crashes'],
                            'mailbox': [
                                {'from': env['from'], 'to': env['to'], 'msg': env['msg']}
                                for env in actor['mailbox']
                            ],
                        }
                        for name, actor in sorted(node['actors'].items())
                    ],
                }
                for node in self._sorted_nodes(cluster)
            ],
        }

    def cluster_status(self, ref: dict[str, Any] | str | None) -> dict[str, Any]:
        """Return per-node liveness/heartbeat status (mirrors ``clusterStatus``)."""
        cluster = self._cluster_of(ref)
        out: dict[str, Any] = {}
        for node in self._sorted_nodes(cluster):
            out[node['id']] = {
                'alive': node['alive'],
                'removed': node['removed'],
                'restarts': node['restarts'],
                'partitions': sorted(cluster['partitions'].get(node['id'], set())),
                'lastHeartbeat': [[k, v] for k, v in sorted(node['last_heartbeat'].items())],
            }
        return out

    # ---------------------------------------------------------------- actors

    def actor_spawn(
        self,
        ref: dict[str, Any] | str | None,
        node_id: str,
        name: str,
        behavior: Behavior,
        initial_state: Any,
    ) -> dict[str, Any]:
        """Spawn an actor on a node; returns an ActorRef ``{__omni_actor, id, node, name}``."""
        cluster = self._cluster_of(ref)
        node = cluster['nodes'].get(node_id)
        if node is None:
            panic(f"sim.actor.spawn: unknown node '{node_id}' in cluster '{cluster['name']}'")
        if not node['alive']:
            panic(f"sim.actor.spawn: node '{node_id}' is not alive")
        if name in node['actors']:
            panic(f"sim.actor.spawn: actor '{name}' already exists on node '{node_id}'")
        if not callable(behavior):
            panic(f"sim.actor.spawn: behavior for '{name}' is not a function")
        actor: dict[str, Any] = {
            'node': node,
            'name': name,
            'id': f'{node_id}/{name}',
            'behavior': behavior,
            'initial_state': initial_state,
            'state': initial_state,
            'mailbox': [],
            'alive': True,
            'stopped': False,
            'restarts': 0,
            'crashes': 0,
            'processed': 0,
        }
        node['actors'][name] = actor
        return {'__omni_actor': True, 'id': actor['id'], 'node': node_id, 'name': name}

    def actor_send(self, ref: dict[str, Any] | str | None, target: Any, msg: Any) -> int:
        """Send ``msg`` to ``target`` (ActorRef, ``node/name``, or bare name)."""
        cluster = self._cluster_of(ref)
        sender = self._sender_id or ''
        source = self._sender_node or cluster['nodes'].get(self._coordinator_id(cluster['name']))
        actor = self._resolve_actor(cluster, target)
        cluster['seq'] += 1
        env: dict[str, Any] = {
            'seq': cluster['seq'],
            'from': sender,
            'to': actor['id'] if actor is not None else None,
            'msg': msg,
            'attempts': 0,
        }
        if actor is None:
            self._dead_letter(cluster, env, 'unknown-actor')
            return cast(int, env['seq'])
        if source is None:
            panic('sim.actor.send: no source node')
        cluster['stats']['sent'] += 1
        source['outbox'].append(env)
        return cast(int, env['seq'])

    def actor_sender(self) -> str:
        """Return the actor id currently processing a message, or ``''``."""
        return self._sender_id

    def actor_receive(
        self, behavior: Behavior, predicate: Predicate | None = None
    ) -> ReceiveBehavior:
        """Wrap ``behavior`` so messages failing ``predicate`` are dropped."""
        return ReceiveBehavior(behavior, predicate)

    def actor_deadletters(self, ref: dict[str, Any] | str | None) -> list[dict[str, Any]]:
        """Return the dead-letter queue for the cluster."""
        return list(self._cluster_of(ref)['stats']['dead_letters'])

    def actor_statistics(self, ref: dict[str, Any] | str | None) -> dict[str, Any]:
        """Return the cluster's delivery counters (mirrors ``actorStatistics``)."""
        s = self._cluster_of(ref)['stats']
        return {
            'sent': s['sent'],
            'delivered': s['delivered'],
            'redelivered': s['redelivered'],
            'dead': s['dead'],
            'crashed': s['crashed'],
            'restarts': s['restarts'],
            'failures': s['failures'],
            'partitions': s['partitions'],
            'heals': s['heals'],
            'steps': s['steps'],
        }

    def actor_step(self, ref: dict[str, Any] | str | None) -> bool:
        """Run one scheduling step; True when any work happened."""
        return self._step_cluster(self._cluster_of(ref))

    def actor_steps(self, ref: dict[str, Any] | str | None, n: int) -> dict[str, Any]:
        """Run exactly ``n`` scheduling steps and return the stats."""
        cluster = self._cluster_of(ref)
        for _ in range(n):
            self._step_cluster(cluster)
        return cast(dict[str, Any], cluster['stats'])

    def actor_run(self, ref: dict[str, Any] | str | None) -> dict[str, Any]:
        """Drain the cluster deterministically (bounded by ``max_steps``)."""
        cluster = self._cluster_of(ref)
        for _ in range(cluster['config']['max_steps']):
            if not self._step_cluster(cluster):
                break
        return cast(dict[str, Any], cluster['stats'])

    # ------------------------------------------------------- flat sim.* aliases

    def cluster(self, name: str, opts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Flat alias for :meth:`cluster_create` on the current runtime."""
        return self.cluster_create(name, opts)

    def node(self, node_id: str) -> dict[str, Any]:
        """Flat alias for :meth:`cluster_add_node` on the current cluster."""
        return self.cluster_add_node(None, node_id)

    def spawn(
        self, node_id: str, name: str, behavior: Behavior, initial_state: Any
    ) -> dict[str, Any]:
        """Flat alias for :meth:`actor_spawn` on the current cluster."""
        return self.actor_spawn(None, node_id, name, behavior, initial_state)

    def send(self, target: Any, msg: Any) -> int:
        """Flat alias for :meth:`actor_send` on the current cluster."""
        return self.actor_send(None, target, msg)

    def sender(self) -> str:
        """Flat alias for :meth:`actor_sender`."""
        return self.actor_sender()

    def partition(self, a: str, b: str) -> None:
        """Flat alias for :meth:`cluster_partition` on the current cluster."""
        self.cluster_partition(None, a, b)

    def heal(self, a: str, b: str) -> None:
        """Flat alias for :meth:`cluster_heal` on the current cluster."""
        self.cluster_heal(None, a, b)

    def fail(self, node_id: str, opts: dict[str, Any] | None = None) -> None:
        """Flat alias for :meth:`cluster_fail` on the current cluster."""
        self.cluster_fail(None, node_id, opts)

    def restart(self, node_id: str) -> bool:
        """Flat alias for :meth:`cluster_restart` on the current cluster."""
        return self.cluster_restart(None, node_id)

    def remove(self, node_id: str) -> None:
        """Flat alias for :meth:`cluster_remove` on the current cluster."""
        self.cluster_remove(None, node_id)

    def stop_actor(self, node_id: str, name: str) -> None:
        """Flat alias for :meth:`cluster_stop_actor` on the current cluster."""
        self.cluster_stop_actor(None, node_id, name)

    def members(self, node_id: str) -> list[str]:
        """Flat alias for :meth:`cluster_members` on the current cluster."""
        return self.cluster_members(None, node_id)

    def deadletters(self) -> list[dict[str, Any]]:
        """Flat alias for :meth:`actor_deadletters` on the current cluster."""
        return self.actor_deadletters(None)

    def stats(self) -> dict[str, Any]:
        """Flat alias for :meth:`actor_statistics` on the current cluster."""
        return self.actor_statistics(None)

    def step(self) -> bool:
        """Flat alias for :meth:`actor_step` on the current cluster."""
        return self.actor_step(None)

    def steps(self, n: int) -> dict[str, Any]:
        """Flat alias for :meth:`actor_steps` on the current cluster."""
        return self.actor_steps(None, n)

    def run(self) -> dict[str, Any]:
        """Flat alias for :meth:`actor_run` on the current cluster."""
        return self.actor_run(None)

    def status(self) -> dict[str, Any]:
        """Flat alias for :meth:`cluster_status` (empty dict without a cluster)."""
        if self._current is None:
            return {}
        return self.cluster_status(None)

    # ------------------------------------------------------------- internals

    def _cluster_of(self, ref: dict[str, Any] | str | None) -> dict[str, Any]:
        if ref is None:
            current = self._current
            if current is None:
                panic('sim.actor: no current cluster (call cluster.create first)')
            return current
        if isinstance(ref, str):
            cluster = self._clusters.get(ref)
            if cluster is None:
                panic(f"sim.actor: unknown cluster '{ref}'")
            return cluster
        return ref

    @staticmethod
    def _coordinator_id(name: str) -> str:
        return f'{name}.coordinator'

    def _cluster_add_node(self, cluster: dict[str, Any], node_id: str) -> dict[str, Any]:
        existing = cluster['nodes'].get(node_id)
        if existing is not None:
            return cast(dict[str, Any], existing)
        node: dict[str, Any] = {
            'id': node_id,
            'alive': True,
            'removed': False,
            'no_restart': False,
            'restarts': 0,
            'actors': {},
            'outbox': [],
            'inbox': [],
            'last_heartbeat': {},
        }
        node['last_heartbeat'][node_id] = cluster['tick']
        cluster['nodes'][node_id] = node
        return node

    def _sorted_nodes(self, cluster: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(cluster['nodes'].values(), key=lambda n: n['id'])

    @staticmethod
    def _node_of_actor_id(cluster: dict[str, Any], actor_id: str) -> dict[str, Any] | None:
        if not actor_id:
            return None
        slash = actor_id.find('/')
        if slash < 0:
            return None
        return cast(dict[str, Any] | None, cluster['nodes'].get(actor_id[:slash]))

    @staticmethod
    def _lookup_actor_by_id(cluster: dict[str, Any], actor_id: str) -> dict[str, Any] | None:
        slash = actor_id.find('/')
        if slash < 0:
            return None
        node = cluster['nodes'].get(actor_id[:slash])
        if node is None or node['removed']:
            return None
        return cast(dict[str, Any] | None, node['actors'].get(actor_id[slash + 1 :]))

    def _resolve_actor(self, cluster: dict[str, Any], target: Any) -> dict[str, Any] | None:
        if isinstance(target, dict) and target.get('__omni_actor'):
            return self._lookup_actor_by_id(cluster, target['id'])
        if isinstance(target, str):
            if '/' in target:
                return self._lookup_actor_by_id(cluster, target)
            for node in self._sorted_nodes(cluster):
                if node['removed']:
                    continue
                actor = node['actors'].get(target)
                if actor is not None:
                    return cast(dict[str, Any], actor)
        return None

    @staticmethod
    def _is_partitioned(cluster: dict[str, Any], a: dict[str, Any], b: dict[str, Any]) -> bool:
        pa = cluster['partitions'].get(a['id'])
        pb = cluster['partitions'].get(b['id'])
        return bool(pa and b['id'] in pa) or bool(pb and a['id'] in pb)

    def _dead_letter(self, cluster: dict[str, Any], env: dict[str, Any], reason: str) -> None:
        if env.get('_dead'):
            return
        env['_dead'] = True
        env['reason'] = reason
        cluster['stats']['dead'] += 1
        cluster['stats']['dead_letters'].append(
            {
                'seq': env['seq'],
                'from': env['from'],
                'to': env['to'],
                'msg': env['msg'],
                'reason': reason,
            }
        )

    def _remove_node(self, cluster: dict[str, Any], node_id: str, reason: str) -> None:
        node = cluster['nodes'].get(node_id)
        if node is None or node['removed']:
            return
        node['alive'] = False
        node['removed'] = True
        for actor in node['actors'].values():
            actor['alive'] = False
            actor['stopped'] = True
        prefix = f'{node_id}/'
        for other in cluster['nodes'].values():
            keep_out: list[dict[str, Any]] = []
            for env in other['outbox']:
                if env.get('to') and env['to'].startswith(prefix):
                    self._dead_letter(cluster, env, reason)
                else:
                    keep_out.append(env)
            other['outbox'] = keep_out
            keep_in: list[dict[str, Any]] = []
            for env in other['inbox']:
                if env.get('to') and env['to'].startswith(prefix):
                    self._dead_letter(cluster, env, reason)
                else:
                    keep_in.append(env)
            other['inbox'] = keep_in
        for actor in node['actors'].values():
            for env in actor['mailbox']:
                self._dead_letter(cluster, env, reason)
            actor['mailbox'] = []

    def _step_cluster(  # noqa: PLR0912, PLR0915 - port of the monolithic JS _stepCluster
        self, cluster: dict[str, Any]
    ) -> bool:
        config = cluster['config']
        cluster['tick'] += 1
        cluster['stats']['steps'] += 1
        work = False

        # 1. heartbeats (every interval, alive nodes ping their peers)
        if cluster['tick'] % config['heartbeat_interval'] == 0:
            alive = [n for n in self._sorted_nodes(cluster) if n['alive'] and not n['removed']]
            for n in alive:
                for m in alive:
                    n['last_heartbeat'][m['id']] = cluster['tick']

        # 2. failure detection — peers we have not heard from are removed
        for n in self._sorted_nodes(cluster):
            if not n['alive'] or n['removed']:
                continue
            for p in cluster['nodes'].values():
                if p['id'] == n['id'] or p['alive'] or p['removed']:
                    continue
                last = n['last_heartbeat'].get(p['id'])
                since = cluster['tick'] if last is None else cluster['tick'] - last
                if since > config['heartbeat_timeout']:
                    cluster['stats']['failures'] += 1
                    self._remove_node(cluster, p['id'], 'detected-dead')
                    work = True

        # 3. supervision — restart crashed nodes; remove unrecoverable ones
        for p in cluster['nodes'].values():
            if p['alive'] or p['removed']:
                continue
            if p['no_restart']:
                continue
            if p['restarts'] < config['max_node_restarts']:
                self.cluster_restart(cluster, p['id'])
                work = True
            else:
                self._remove_node(cluster, p['id'], 'restart-limit')
                work = True

        # 4. deliver outboxes -> target node inboxes (held while partitioned/dead)
        for n in self._sorted_nodes(cluster):
            if not n['alive'] or n['removed']:
                continue
            keep: list[dict[str, Any]] = []
            for env in n['outbox']:
                if env.get('_dead'):
                    continue
                actor = self._resolve_actor(cluster, env['to'])
                if actor is None:
                    self._dead_letter(cluster, env, 'actor-gone')
                    work = True
                    continue
                target_node = actor['node']
                if not target_node['alive'] or target_node['removed']:
                    env['attempts'] += 1
                    if env['attempts'] > _FIRST_ATTEMPT:
                        cluster['stats']['redelivered'] += 1
                    keep.append(env)
                    continue
                if self._is_partitioned(cluster, n, target_node):
                    env['attempts'] += 1
                    if env['attempts'] > _FIRST_ATTEMPT:
                        cluster['stats']['redelivered'] += 1
                    keep.append(env)
                    continue
                env['attempts'] += 1
                if env['attempts'] > _FIRST_ATTEMPT:
                    cluster['stats']['redelivered'] += 1
                target_node['inbox'].append(env)
                work = True
            n['outbox'] = keep

        # 5. inboxes -> actor mailboxes
        for n in self._sorted_nodes(cluster):
            if not n['alive'] or n['removed']:
                continue
            inbox = n['inbox']
            n['inbox'] = []
            for env in inbox:
                if env.get('_dead'):
                    continue
                actor = self._resolve_actor(cluster, env['to'])
                if actor is None or not actor['alive'] or actor['stopped']:
                    self._dead_letter(cluster, env, 'actor-gone')
                    work = True
                else:
                    actor['mailbox'].append(env)
                    work = True

        # 6. process one message per actor (sorted node, sorted name, FIFO mailbox)
        for n in self._sorted_nodes(cluster):
            if not n['alive'] or n['removed']:
                continue
            for name in sorted(n['actors']):
                actor = n['actors'][name]
                if not actor['alive'] or actor['stopped']:
                    continue
                if not actor['mailbox']:
                    continue
                env = actor['mailbox'].pop(0)
                work = True
                next_state = None
                crashed = False
                try:
                    self._sender_id = env['from']
                    self._sender_node = self._node_of_actor_id(cluster, env['from'])
                    next_state = actor['behavior'](
                        actor['state'],
                        env['msg'],
                        {
                            'self': actor['id'],
                            'node': actor['node']['id'],
                            'sender': env['from'],
                        },
                    )
                except Exception:  # noqa: BLE001 - mirrors the JS catch-all
                    crashed = True
                    actor['crashes'] += 1
                    cluster['stats']['crashed'] += 1
                    self._dead_letter(cluster, env, 'crash')
                    if actor['restarts'] < config['max_actor_restarts']:
                        actor['restarts'] += 1
                        cluster['stats']['restarts'] += 1
                        actor['state'] = actor['initial_state']
                        work = True
                    else:
                        actor['alive'] = False
                        actor['stopped'] = True
                        for pending in actor['mailbox']:
                            self._dead_letter(cluster, pending, 'actor-stopped')
                        actor['mailbox'] = []
                finally:
                    self._sender_id = ''
                    self._sender_node = None
                if not crashed:
                    if next_state is not None:
                        actor['state'] = next_state
                    actor['processed'] += 1
                    cluster['stats']['delivered'] += 1

        return work


def create_runtime() -> ActorRuntime:
    """Return a fresh :class:`ActorRuntime` (mirrors ``createRuntime().sim``)."""
    return ActorRuntime()


__all__ = ['ActorRuntime', 'ReceiveBehavior', 'VERSION', 'create_runtime']
