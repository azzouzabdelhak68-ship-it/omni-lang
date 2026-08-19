"""Property tests for OMNISYS.pkg."""

from __future__ import annotations

import json

import omnisys_pkg as pkg
from hypothesis import given
from hypothesis import strategies as st

_NAMES = st.text(alphabet='abcdefghijklmnopqrstuvwxyz-', min_size=1, max_size=16)
_VERSIONS = st.text(alphabet='0123456789.', min_size=1, max_size=8)


@given(_NAMES, _VERSIONS)
def test_registry_add_get_round_trip(name: str, version: str) -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create(name, version, {}), None)
    spec = pkg.registry_get(registry, name, version)
    assert spec is not None
    assert spec['name'] == name
    assert spec['version'] == version


@given(_NAMES, _VERSIONS)
def test_registry_add_get_default_version(name: str, version: str) -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create(name, version, {}), None)
    spec = pkg.registry_get(registry, name, None)
    assert spec is not None
    assert spec['version'] == version


@given(_NAMES, _VERSIONS)
def test_resolve_single_returns_spec(name: str, version: str) -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create(name, version, {}), None)
    order = pkg.resolve(name, version, registry)
    assert len(order) == 1
    assert order[0]['name'] == name


@given(_NAMES, _VERSIONS, st.lists(_NAMES, min_size=0, max_size=5))
def test_resolve_chain_has_no_duplicates(name: str, version: str, deps: list[str]) -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create(name, version, {d: '1' for d in deps}), None)
    for dep in dict.fromkeys(deps):
        pkg.registry_add(registry, pkg.create(dep, '1', {}), None)
    order = pkg.resolve(name, version, registry)
    keys = [spec['name'] + '@' + spec['version'] for spec in order]
    assert len(keys) == len(set(keys))


@given(_NAMES, _VERSIONS, st.lists(_NAMES, min_size=0, max_size=5))
def test_list_dependencies_matches_create(name: str, version: str, deps: list[str]) -> None:
    spec = pkg.create(name, version, {d: '1' for d in deps})
    assert pkg.list_dependencies(spec) == list(dict.fromkeys(deps))


def test_create_then_manifest_round_trip(tmp_path) -> None:
    for spec in [
        pkg.create('app', '1.0.0', {'dep': '1'}),
        pkg.create('tool', '2.1.0', {}),
    ]:
        manifest_path = tmp_path / 'pkg.json'
        manifest_path.write_text(json.dumps(spec), encoding='utf-8')
        assert pkg.manifest(str(manifest_path)) == spec
