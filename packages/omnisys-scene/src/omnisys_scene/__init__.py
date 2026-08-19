"""OMNISYS.scene — portable 3D scene graph.

Python reference implementation of the OMNISYS ``scene`` module (v6): a
scene is a plain dict holding nodes (group/mesh/camera/light) with
transforms (position/rotation/scale), a ``children`` tree, and an ``order``
list. Mirrors the JS reference lane ``omnisys/scene.js`` and satisfies the
registry contract (``OMNISYS_MODULES["scene"]``): all eleven functions are
pure (zero declared effects) and depend only on ``omnisys_core.panic`` for
the shared unknown-parent/node errors. Hardware renderers are escapes that
consume the same JSON-able scene model.
"""

from copy import deepcopy
from typing import Any, TypeAlias, cast

from omnisys_core import panic

__all__ = [
    'new_scene',
    'node',
    'mesh',
    'camera',
    'light',
    'add',
    'transform',
    'remove',
    'snapshot',
    'update',
    'to_json',
]

Scene: TypeAlias = dict[str, Any]
Node: TypeAlias = dict[str, Any]


def new_scene() -> Scene:
    """Return an empty scene value ``{"tag": "scene", "nodes": {}, ...}``."""
    return {'tag': 'scene', 'nodes': {}, 'order': [], 'nextId': 1}


def _node_base(id_: str, kind: str) -> Node:
    """Return the base node value for ``id_`` with the given ``kind``."""
    return {
        'id': id_,
        'kind': kind,
        'children': [],
        'transform': {'position': [0, 0, 0], 'rotation': [0, 0, 0], 'scale': [1, 1, 1]},
    }


def _ensure_node(s: Scene, id_: str, kind: str) -> Node:
    """Return the node for ``id_`` in ``s``, creating it when missing."""
    nodes = cast(dict[str, Node], s['nodes'])
    if id_ not in nodes:
        nodes[id_] = _node_base(id_, kind)
        s['order'].append(id_)
    return nodes[id_]


def node(s: Scene, id_: str) -> Node:
    """Return the group node ``str(id_)``, creating it when missing."""
    return _ensure_node(s, str(id_), 'group')


def mesh(s: Scene, id_: str, geometry: str) -> Node:
    """Return the mesh node ``str(id_)`` with ``str(geometry)`` set."""
    node_ = _ensure_node(s, str(id_), 'mesh')
    node_['geometry'] = str(geometry)
    return node_


def camera(s: Scene, id_: str) -> Node:
    """Return the camera node ``str(id_)``, creating it when missing."""
    return _ensure_node(s, str(id_), 'camera')


def light(s: Scene, id_: str, kind: str = 'directional') -> Node:
    """Return the light node ``str(id_)`` with ``lightType`` set."""
    node_ = _ensure_node(s, str(id_), 'light')
    node_['lightType'] = str(kind or 'directional')
    return node_


def add(s: Scene, parent: str, child: str) -> Scene:
    """Wire ``child`` under ``parent`` once; panic when ``parent`` is unknown."""
    nodes = cast(dict[str, Node], s['nodes'])
    parent_node = nodes.get(parent)
    if parent_node is None:
        panic('scene.add: unknown parent ' + parent)
    _ensure_node(s, child, 'group')
    if child not in parent_node['children']:
        parent_node['children'].append(child)
    return s


def transform(s: Scene, id_: str, attrs: dict[str, Any]) -> Scene:
    """Apply position/rotation/scale from ``attrs``; panic when ``id_`` unknown."""
    nodes = cast(dict[str, Node], s['nodes'])
    node_ = nodes.get(id_)
    if node_ is None:
        panic('scene.transform: unknown node ' + id_)
    for key in ('position', 'rotation', 'scale'):
        value = attrs.get(key)
        if value is not None:
            node_['transform'][key] = value
    return s


def remove(s: Scene, id_: str) -> Scene:
    """Delete the node ``id_`` and its order entry, then return ``s``."""
    if id_ in s['nodes']:
        del s['nodes'][id_]
    s['order'] = [x for x in s['order'] if x != id_]
    return s


def snapshot(s: Scene) -> Scene:
    """Return a deep copy of ``s`` containing only its nodes and order."""
    return deepcopy({'nodes': s['nodes'], 'order': s['order']})


def update(s: Scene, dt: float) -> Scene:
    """Increment every node's ``_elapsed`` by ``dt`` and return ``s``."""
    nodes = cast(dict[str, Node], s['nodes'])
    for id_ in s['order']:
        node_ = nodes.get(id_)
        if node_ is not None:
            node_['_elapsed'] = node_.get('_elapsed', 0) + dt
    return s


def to_json(s: Scene) -> Scene:
    """Return the JSON-able snapshot of ``s`` (nodes + order only)."""
    return snapshot(s)
