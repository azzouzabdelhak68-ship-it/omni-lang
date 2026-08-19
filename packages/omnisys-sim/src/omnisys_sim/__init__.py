"""OMNISYS.sim — a portable ECS/simulation model.

Python reference implementation of the OMNISYS ``sim`` module (v6): a world
is a plain dict holding entities with component maps, an insertion-ordered
name list, and a list of systems; ``run`` steps the world deterministically.
Mirrors the JS reference lane ``omnisys/sim.js`` and satisfies the registry
contract (``OMNISYS_MODULES["sim"]``): all ten functions are pure (zero
declared effects) and depend on ``omnisys_core.panic`` for the shared
unknown-entity error. The JS lane's ``sim.actor`` distributed bridge is a
Node-only escape (v5.3 ``simulation_engine/runtime.js``) and is not ported.
"""

from collections.abc import Callable
from copy import deepcopy
from typing import Any, TypeAlias, cast

from omnisys_core import panic

__all__ = [
    'world',
    'entity',
    'component',
    'get',
    'system',
    'run',
    'query',
    'remove_entity',
    'snapshot',
    'entities',
]

World: TypeAlias = dict[str, Any]
Entity: TypeAlias = dict[str, Any]
SystemFn: TypeAlias = Callable[[World], Any]


def world() -> World:
    """Return an empty world value ``{"tag": "world", "entities": {}, ...}``."""
    return {'tag': 'world', 'entities': {}, 'order': [], 'systems': [], 'step': 0}


def entity(world: World, name: str) -> Entity:
    """Return the entity ``name``, creating it (with a component map) when missing."""
    entities = cast(dict[str, Entity], world['entities'])
    if name not in entities:
        entities[name] = {'tag': 'entity', 'name': name, 'components': {}}
        world['order'].append(name)
    return entities[name]


def component(world: World, name: str, component: Any, value: Any) -> World:
    """Set ``str(component)`` on entity ``name`` and return the same world."""
    entity_ = entity(world, name)
    cast(dict[str, Any], entity_['components'])[str(component)] = value
    return world


def get(world: World, name: str, component: Any) -> Any:
    """Return the ``str(component)`` value of entity ``name``; panic when unknown."""
    entity_ = world['entities'].get(name)
    if entity_ is None:
        panic('sim.get: unknown entity ' + name)
    return cast(dict[str, Any], entity_['components']).get(str(component))


def system(world: World, fn: SystemFn) -> World:
    """Register ``fn`` in the system chain (registration order) and return the world."""
    cast(list[SystemFn], world['systems']).append(fn)
    return world


def run(world: World, steps: int) -> World:
    """Run every system once per step (in registration order), then return the world."""
    systems = cast(list[SystemFn], world['systems'])
    for _ in range(max(0, int(steps))):
        for fn in systems:
            fn(world)
        world['step'] += 1
    return world


def query(world: World, component: Any) -> list[str]:
    """Return the entity names (in order) whose component map has ``str(component)``."""
    entities = cast(dict[str, Entity], world['entities'])
    return [
        name
        for name in cast(list[str], world['order'])
        if str(component) in cast(dict[str, Any], entities.get(name, {}).get('components', {}))
    ]


def remove_entity(world: World, name: str) -> World:
    """Remove entity ``name`` and its order entry, then return the same world."""
    cast(dict[str, Entity], world['entities']).pop(name, None)
    world['order'] = [x for x in cast(list[str], world['order']) if x != name]
    return world


def entities(world: World) -> list[str]:
    """Return a copy of the insertion-ordered entity names."""
    return cast(list[str], world['order'])[:]


def snapshot(world: World) -> World:
    """Return a deep copy of ``world`` without its system chain."""
    return {
        'tag': 'world',
        'step': cast(int, world['step']),
        'entities': deepcopy(world['entities']),
        'order': cast(list[str], world['order'])[:],
    }
