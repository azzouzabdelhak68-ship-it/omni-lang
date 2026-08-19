"""Unit tests for OMNISYS.pkg."""

from __future__ import annotations

import json

import omnisys_pkg as pkg


# =============================================================================
# Original pkg module tests (backward compatibility)
# =============================================================================

def test_create_shape() -> None:
    spec = pkg.create('app', '1.0.0', {'lodash': '2.0.0'})
    expected = {
        'tag': 'package',
        'name': 'app',
        'version': '1.0.0',
        'dependencies': {'lodash': '2.0.0'},
    }
    assert spec == expected


def test_create_coerces_name_version() -> None:
    spec = pkg.create(42, 7, None)
    assert spec['name'] == '42'
    assert spec['version'] == '7'
    assert spec['dependencies'] == {}


def test_create_default_deps_empty() -> None:
    spec = pkg.create('a', '1', None)
    assert spec['dependencies'] == {}


def test_registry_add_nested() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    assert registry['a']['1.0.0']['name'] == 'a'
    assert registry['a']['1.0.0']['version'] == '1.0.0'
    assert registry['a']['1.0.0']['dependencies'] == {}


def test_registry_add_multiple_versions() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    pkg.registry_add(registry, pkg.create('a', '2.0.0', {}), None)
    assert set(registry['a']) == {'1.0.0', '2.0.0'}


def test_registry_add_version_alias() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), 'latest')
    assert registry['latest'] is registry['a']


def test_registry_add_no_alias_when_none() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    assert 'latest' not in registry


def test_registry_add_overwrites_same_version() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {'x': '1'}), None)
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {'y': '2'}), None)
    assert registry['a']['1.0.0']['dependencies'] == {'y': '2'}


def test_registry_get_by_version() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    pkg.registry_add(registry, pkg.create('a', '2.0.0', {}), None)
    assert pkg.registry_get(registry, 'a', '2.0.0')['version'] == '2.0.0'


def test_registry_get_default_version() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    assert pkg.registry_get(registry, 'a', None)['version'] == '1.0.0'


def test_registry_get_missing_name() -> None:
    assert pkg.registry_get({}, 'nope', '1.0.0') is None


def test_registry_get_missing_version() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    assert pkg.registry_get(registry, 'a', '9.9.9') is None


def test_registry_get_coerces_name() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('42', '1.0.0', {}), None)
    assert pkg.registry_get(registry, 42, None)['version'] == '1.0.0'


def test_list_dependencies() -> None:
    spec = pkg.create('a', '1', {'x': '1', 'y': '2'})
    assert pkg.list_dependencies(spec) == ['x', 'y']


def test_list_dependencies_empty() -> None:
    assert pkg.list_dependencies(pkg.create('a', '1', {})) == []


def test_list_dependencies_missing_key() -> None:
    assert pkg.list_dependencies({'tag': 'package'}) == []


def test_resolve_single() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    order = pkg.resolve('a', '1.0.0', registry)
    assert len(order) == 1
    assert order[0]['name'] == 'a'


def test_resolve_chain_bfs_order() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1', {'b': '1', 'c': '1'}), None)
    pkg.registry_add(registry, pkg.create('b', '1', {}), None)
    pkg.registry_add(registry, pkg.create('c', '1', {}), None)
    order = pkg.resolve('a', '1', registry)
    names = [spec['name'] for spec in order]
    assert names == ['a', 'b', 'c']


def test_resolve_diamond_dedupe() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1', {'b': '1', 'c': '1'}), None)
    pkg.registry_add(registry, pkg.create('b', '1', {'d': '1'}), None)
    pkg.registry_add(registry, pkg.create('c', '1', {'d': '1'}), None)
    pkg.registry_add(registry, pkg.create('d', '1', {}), None)
    order = pkg.resolve('a', '1', registry)
    names = [spec['name'] for spec in order]
    assert names.count('d') == 1


def test_resolve_unknown_dep_skipped() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1', {'missing': '1'}), None)
    order = pkg.resolve('a', '1', registry)
    assert len(order) == 1
    assert order[0]['name'] == 'a'


def test_resolve_missing_root() -> None:
    assert pkg.resolve('ghost', '1', {}) == []


def test_resolve_defaults_version_to_latest() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', 'latest', {}), None)
    order = pkg.resolve('a', None, registry)
    assert order[0]['name'] == 'a'


def test_resolve_missing_version_returns_empty() -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1', {}), None)
    assert pkg.resolve('a', None, registry) == []


def test_manifest_reads_and_decodes(tmp_path) -> None:
    manifest_path = tmp_path / 'omni.pkg.json'
    manifest_path.write_text(json.dumps({'name': 'app', 'version': '1.0.0'}), encoding='utf-8')
    data = pkg.manifest(str(manifest_path))
    assert data == {'name': 'app', 'version': '1.0.0'}


def test_install_writes_files(tmp_path) -> None:
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1.0.0', {}), None)
    pkg.registry_add(registry, pkg.create('b', '2.0.0', {}), None)
    result = pkg.install(str(tmp_path), registry)
    assert result == {'tag': 'install', 'dir': str(tmp_path), 'count': 2}
    a_file = tmp_path / 'a-1.0.0.pkg.json'
    b_file = tmp_path / 'b-2.0.0.pkg.json'
    assert a_file.exists()
    assert b_file.exists()
    expected = {'name': 'a', 'version': '1.0.0', 'dependencies': {}}
    assert json.loads(a_file.read_text(encoding='utf-8')) == expected


def test_install_creates_dir(tmp_path) -> None:
    target = tmp_path / 'sub' / 'dir'
    registry = {}
    pkg.registry_add(registry, pkg.create('a', '1', {}), None)
    pkg.install(str(target), registry)
    assert (target / 'a-1.pkg.json').exists()


# =============================================================================
# Semantic Versioning tests
# =============================================================================

def test_parse_version_basic() -> None:
    v = pkg.parse_version('1.2.3')
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease == ''
    assert v.build == ''


def test_parse_version_with_prerelease() -> None:
    v = pkg.parse_version('1.2.3-alpha.1')
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease == 'alpha.1'
    assert v.build == ''


def test_parse_version_with_build() -> None:
    v = pkg.parse_version('1.2.3+build.123')
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease == ''
    assert v.build == 'build.123'


def test_parse_version_full() -> None:
    v = pkg.parse_version('2.0.0-beta.4+sha.abc123')
    assert v.major == 2
    assert v.minor == 0
    assert v.patch == 0
    assert v.prerelease == 'beta.4'
    assert v.build == 'sha.abc123'


def test_parse_version_zero() -> None:
    v = pkg.parse_version('0.0.1')
    assert v.major == 0
    assert v.minor == 0
    assert v.patch == 1


def test_parse_version_str_roundtrip() -> None:
    for version in ['1.0.0', '2.3.4-alpha', '0.0.1+build', '10.20.30-rc.1+sha.abc']:
        v = pkg.parse_version(version)
        assert str(v) == version


def test_parse_version_invalid() -> None:
    for invalid in ['1', '1.2', '1.2.3.4', 'a.b.c', '1.2.3-', '1.2.3+', '']:
        try:
            pkg.parse_version(invalid)
            assert False, f'Should have raised for {invalid!r}'
        except ValueError:
            pass


def test_version_ordering() -> None:
    v1 = pkg.parse_version('1.0.0')
    v2 = pkg.parse_version('2.0.0')
    v3 = pkg.parse_version('1.1.0')
    v4 = pkg.parse_version('1.0.1')
    v5 = pkg.parse_version('1.0.0-alpha')
    v6 = pkg.parse_version('1.0.0-beta')
    v7 = pkg.parse_version('1.0.0')
    
    assert v1 < v2
    assert v1 < v3
    assert v1 < v4
    assert v5 < v7  # prerelease < release
    assert v5 < v6  # alpha < beta


def test_satisfies_exact() -> None:
    assert pkg.satisfies('1.2.3', '1.2.3')
    assert pkg.satisfies('1.2.3', '=1.2.3')
    assert pkg.satisfies('1.2.3', '==1.2.3')
    assert not pkg.satisfies('1.2.3', '1.2.4')


def test_satisfies_ranges() -> None:
    assert pkg.satisfies('1.2.3', '>=1.2.3')
    assert pkg.satisfies('1.2.4', '>=1.2.3')
    assert not pkg.satisfies('1.2.2', '>=1.2.3')
    
    assert pkg.satisfies('1.2.3', '<=1.2.3')
    assert pkg.satisfies('1.2.2', '<=1.2.3')
    assert not pkg.satisfies('1.2.4', '<=1.2.3')
    
    assert pkg.satisfies('1.2.4', '>1.2.3')
    assert not pkg.satisfies('1.2.3', '>1.2.3')
    
    assert pkg.satisfies('1.2.2', '<1.2.3')
    assert not pkg.satisfies('1.2.3', '<1.2.3')


def test_satisfies_caret() -> None:
    # ^1.2.3 := >=1.2.3 <2.0.0
    assert pkg.satisfies('1.2.3', '^1.2.3')
    assert pkg.satisfies('1.2.4', '^1.2.3')
    assert pkg.satisfies('1.3.0', '^1.2.3')
    assert pkg.satisfies('1.9.9', '^1.2.3')
    assert not pkg.satisfies('2.0.0', '^1.2.3')
    assert not pkg.satisfies('1.2.2', '^1.2.3')
    
    # ^0.2.3 := >=0.2.3 <0.3.0
    assert pkg.satisfies('0.2.3', '^0.2.3')
    assert pkg.satisfies('0.2.4', '^0.2.3')
    assert not pkg.satisfies('0.3.0', '^0.2.3')
    
    # ^0.0.3 := >=0.0.3 <0.0.4
    assert pkg.satisfies('0.0.3', '^0.0.3')
    assert not pkg.satisfies('0.0.4', '^0.0.3')


def test_satisfies_tilde() -> None:
    # ~1.2.3 := >=1.2.3 <1.3.0
    assert pkg.satisfies('1.2.3', '~1.2.3')
    assert pkg.satisfies('1.2.4', '~1.2.3')
    assert pkg.satisfies('1.2.99', '~1.2.3')
    assert not pkg.satisfies('1.3.0', '~1.2.3')
    assert not pkg.satisfies('1.2.2', '~1.2.3')
    
    # ~1.2 := >=1.2.0 <1.3.0
    assert pkg.satisfies('1.2.0', '~1.2')
    assert pkg.satisfies('1.2.5', '~1.2')
    assert not pkg.satisfies('1.3.0', '~1.2')
    
    # ~1 := >=1.0.0 <2.0.0
    assert pkg.satisfies('1.0.0', '~1')
    assert pkg.satisfies('1.9.9', '~1')
    assert not pkg.satisfies('2.0.0', '~1')


def test_satisfies_union() -> None:
    assert pkg.satisfies('1.2.3', '^1.2.3 || >=2.0.0')
    assert pkg.satisfies('2.0.0', '^1.2.3 || >=2.0.0')
    assert pkg.satisfies('2.5.0', '^1.2.3 || >=2.0.0')
    assert not pkg.satisfies('1.1.0', '^1.2.3 || >=2.0.0')
    assert not pkg.satisfies('0.9.0', '^1.2.3 || >=2.0.0')


def test_satisfies_prerelease() -> None:
    # Prereleases only match if explicitly included in the range
    assert not pkg.satisfies('1.0.0-alpha', '^1.0.0')  # ^1.0.0 is a release range
    assert pkg.satisfies('1.0.0-alpha', '>=1.0.0-alpha')  # explicit prerelease range
    assert pkg.satisfies('1.0.0-alpha', '^1.0.0-alpha')  # ^ on prerelease base


# =============================================================================
# Checksum tests
# =============================================================================

def test_compute_checksum() -> None:
    checksum = pkg.compute_checksum(b'hello world')
    assert checksum.startswith('sha256:') or len(checksum) == 64  # hex string
    assert len(checksum) >= 64


def test_compute_checksum_deterministic() -> None:
    c1 = pkg.compute_checksum(b'same content')
    c2 = pkg.compute_checksum(b'same content')
    assert c1 == c2


def test_compute_checksum_different() -> None:
    c1 = pkg.compute_checksum(b'content 1')
    c2 = pkg.compute_checksum(b'content 2')
    assert c1 != c2


# =============================================================================
# Lockfile tests
# =============================================================================

def test_lockfile_entry_roundtrip() -> None:
    entry = pkg.LockfileEntry(
        name='test-pkg',
        version='1.2.3',
        checksum='sha256:abc123',
        dependencies={'dep1': '2.0.0', 'dep2': '3.1.0'}
    )
    d = entry.to_dict()
    assert d['name'] == 'test-pkg'
    assert d['version'] == '1.2.3'
    assert d['checksum'] == 'sha256:abc123'
    assert d['dependencies'] == {'dep1': '2.0.0', 'dep2': '3.1.0'}
    
    entry2 = pkg.LockfileEntry.from_dict(d)
    assert entry2.name == entry.name
    assert entry2.version == entry.version
    assert entry2.checksum == entry.checksum
    assert entry2.dependencies == entry.dependencies


def test_lockfile_roundtrip() -> None:
    entries = (
        pkg.LockfileEntry('a', '1.0.0', 'sha256:aaa', {}),
        pkg.LockfileEntry('b', '2.0.0', 'sha256:bbb', {'a': '1.0.0'}),
    )
    lf = pkg.Lockfile(packages=entries, metadata={'resolved_at': '2024-01-01'})
    
    # JSON roundtrip
    json_str = lf.to_json()
    lf2 = pkg.Lockfile.from_json(json_str)
    
    assert len(lf2.packages) == 2
    assert lf2.packages[0].name == 'a'
    assert lf2.packages[1].name == 'b'
    assert lf2.metadata == {'resolved_at': '2024-01-01'}
    
    # Dict roundtrip
    d = lf.to_dict()
    lf3 = pkg.Lockfile.from_dict(d)
    assert len(lf3.packages) == 2


def test_lockfile_get() -> None:
    entries = (
        pkg.LockfileEntry('a', '1.0.0', 'sha256:aaa', {}),
        pkg.LockfileEntry('b', '2.0.0', 'sha256:bbb', {}),
    )
    lf = pkg.Lockfile(packages=entries)
    
    a = lf.get('a')
    assert a is not None
    assert a.version == '1.0.0'
    
    b = lf.get('b')
    assert b is not None
    assert b.version == '2.0.0'
    
    assert lf.get('missing') is None


# =============================================================================
# PackageSpec tests
# =============================================================================

def test_package_spec_roundtrip() -> None:
    spec = pkg.PackageSpec(
        name='my-pkg',
        version_constraint='^1.2.3',
        dependencies={'dep': '^2.0.0'},
        checksum='sha256:abc'
    )
    d = spec.to_dict()
    assert d['name'] == 'my-pkg'
    assert d['version'] == '^1.2.3'
    assert d['dependencies'] == {'dep': '^2.0.0'}
    assert d['checksum'] == 'sha256:abc'
    
    spec2 = pkg.PackageSpec.from_dict(d)
    assert spec2.name == spec.name
    assert spec2.version_constraint == spec.version_constraint
    assert spec2.dependencies == spec.dependencies
    assert spec2.checksum == spec.checksum


def test_package_spec_from_dict_legacy_version_key() -> None:
    # Support legacy 'version' key
    spec = pkg.PackageSpec.from_dict({'name': 'x', 'version': '1.0.0', 'dependencies': {}})
    assert spec.version_constraint == '1.0.0'


# =============================================================================
# Version Resolution tests
# =============================================================================

def test_resolve_versions_simple() -> None:
    registry = {
        'app': {
            '1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}},
            '2.0.0': {'name': 'app', 'version': '2.0.0', 'dependencies': {}},
        }
    }
    specs = [pkg.PackageSpec('app', '^1.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert len(resolution.packages) == 1
    assert resolution.packages[0].name == 'app'
    assert resolution.packages[0].version == '1.0.0'  # highest matching ^1.0.0


def test_resolve_versions_with_dependency() -> None:
    registry = {
        'app': {
            '1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {'lib': '^2.0.0'}},
        },
        'lib': {
            '2.0.0': {'name': 'lib', 'version': '2.0.0', 'dependencies': {}},
            '2.1.0': {'name': 'lib', 'version': '2.1.0', 'dependencies': {}},
            '3.0.0': {'name': 'lib', 'version': '3.0.0', 'dependencies': {}},
        }
    }
    specs = [pkg.PackageSpec('app', '1.0.0', {'lib': '^2.0.0'})]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert len(resolution.packages) == 2
    # lib should come before app (dependency order)
    assert resolution.packages[0].name == 'lib'
    assert resolution.packages[1].name == 'app'
    # Should pick highest matching ^2.0.0 which is 2.1.0
    assert resolution.packages[0].version == '2.1.0'


def test_resolve_versions_diamond() -> None:
    registry = {
        'app': {
            '1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {'left': '1.0.0', 'right': '1.0.0'}},
        },
        'left': {
            '1.0.0': {'name': 'left', 'version': '1.0.0', 'dependencies': {'shared': '1.0.0'}},
        },
        'right': {
            '1.0.0': {'name': 'right', 'version': '1.0.0', 'dependencies': {'shared': '1.0.0'}},
        },
        'shared': {
            '1.0.0': {'name': 'shared', 'version': '1.0.0', 'dependencies': {}},
        }
    }
    specs = [pkg.PackageSpec('app', '1.0.0', {'left': '1.0.0', 'right': '1.0.0'})]
    resolution = pkg.resolve_versions(specs, registry)
    
    names = [p.name for p in resolution.packages]
    # shared should appear only once
    assert names.count('shared') == 1
    # shared should be before left and right
    shared_idx = names.index('shared')
    left_idx = names.index('left')
    right_idx = names.index('right')
    assert shared_idx < left_idx
    assert shared_idx < right_idx
    # app should be last
    assert names[-1] == 'app'


def test_resolve_versions_with_lockfile_prefers_locked() -> None:
    registry = {
        'app': {
            '1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}},
            '2.0.0': {'name': 'app', 'version': '2.0.0', 'dependencies': {}},
        }
    }
    lockfile = pkg.Lockfile(packages=(
        pkg.LockfileEntry('app', '1.0.0', 'sha256:locked', {}),
    ))
    specs = [pkg.PackageSpec('app', '^1.0.0', {})]  # Could match 2.0.0 but locked to 1.0.0
    resolution = pkg.resolve_versions(specs, registry, lockfile)
    
    assert resolution.packages[0].version == '1.0.0'


def test_resolve_versions_lockfile_upgrade_when_needed() -> None:
    registry = {
        'app': {
            '1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}},
            '2.0.0': {'name': 'app', 'version': '2.0.0', 'dependencies': {}},
        }
    }
    # Lockfile has 1.0.0 but constraint is ^2.0.0 (incompatible)
    lockfile = pkg.Lockfile(packages=(
        pkg.LockfileEntry('app', '1.0.0', 'sha256:old', {}),
    ))
    specs = [pkg.PackageSpec('app', '^2.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry, lockfile)
    
    # Should upgrade to 2.0.0 since locked version doesn't satisfy constraint
    assert resolution.packages[0].version == '2.0.0'


def test_resolve_versions_circular_dependency_warning() -> None:
    registry = {
        'a': {'1.0.0': {'name': 'a', 'version': '1.0.0', 'dependencies': {'b': '1.0.0'}}},
        'b': {'1.0.0': {'name': 'b', 'version': '1.0.0', 'dependencies': {'a': '1.0.0'}}},
    }
    specs = [
        pkg.PackageSpec('a', '1.0.0', {'b': '1.0.0'}),
        pkg.PackageSpec('b', '1.0.0', {'a': '1.0.0'}),
    ]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert any('Circular dependency' in w for w in resolution.warnings)


def test_resolve_versions_missing_package_warning() -> None:
    registry = {}
    specs = [pkg.PackageSpec('missing', '1.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert any('No version found' in w for w in resolution.warnings)
    assert len(resolution.packages) == 0
    assert len(resolution.packages) == 0


def test_resolve_versions_no_matching_version_warning() -> None:
    registry = {'app': {'1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}}}}
    specs = [pkg.PackageSpec('app', '>=2.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert any('No version found' in w for w in resolution.warnings)


def test_resolution_to_lockfile() -> None:
    registry = {
        'app': {'1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {'lib': '1.0.0'}}},
        'lib': {'1.0.0': {'name': 'lib', 'version': '1.0.0', 'dependencies': {}}},
    }
    specs = [pkg.PackageSpec('app', '1.0.0', {'lib': '1.0.0'})]
    resolution = pkg.resolve_versions(specs, registry)
    
    lockfile = resolution.to_lockfile()
    assert len(lockfile.packages) == 2
    assert lockfile.get('lib') is not None
    assert lockfile.get('app') is not None


def test_resolution_to_list() -> None:
    registry = {
        'app': {'1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}}},
    }
    specs = [pkg.PackageSpec('app', '1.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry)
    
    lst = resolution.to_list()
    assert len(lst) == 1
    assert lst[0]['name'] == 'app'
    assert lst[0]['version'] == '1.0.0'


# =============================================================================
# Integration tests (full workflow)
# =============================================================================

def test_full_workflow_manifest_to_lockfile(tmp_path) -> None:
    """Test: manifest -> registry -> resolve -> lockfile -> JSON"""
    # Create a manifest
    manifest = {
        'name': 'my-app',
        'version': '1.0.0',
        'dependencies': {
            'utils': '^1.0.0',
            'core': '^2.0.0',
        }
    }
    manifest_path = tmp_path / 'omni.pkg.json'
    manifest_path.write_text(json.dumps(manifest))
    
    # Read manifest
    loaded = pkg.manifest(str(manifest_path))
    assert loaded == manifest
    
    # Build registry (simulating registry fetch)
    registry = {
        'my-app': {
            '1.0.0': {'name': 'my-app', 'version': '1.0.0', 'dependencies': {'utils': '^1.0.0', 'core': '^2.0.0'}},
        },
        'utils': {
            '1.0.0': {'name': 'utils', 'version': '1.0.0', 'dependencies': {}},
            '1.1.0': {'name': 'utils', 'version': '1.1.0', 'dependencies': {}},
            '2.0.0': {'name': 'utils', 'version': '2.0.0', 'dependencies': {}},
        },
        'core': {
            '2.0.0': {'name': 'core', 'version': '2.0.0', 'dependencies': {}},
            '2.1.0': {'name': 'core', 'version': '2.1.0', 'dependencies': {}},
            '3.0.0': {'name': 'core', 'version': '3.0.0', 'dependencies': {}},
        }
    }
    
    # Resolve
    specs = [
        pkg.PackageSpec('my-app', '1.0.0', {'utils': '^1.0.0', 'core': '^2.0.0'}),
        pkg.PackageSpec('utils', '^1.0.0', {}),
        pkg.PackageSpec('core', '^2.0.0', {}),
    ]
    resolution = pkg.resolve_versions(specs, registry)
    
    # Verify resolution
    names = [p.name for p in resolution.packages]
    assert names == ['utils', 'core', 'my-app']  # deps first
    assert resolution.packages[0].version == '1.1.0'  # highest ^1.0.0
    assert resolution.packages[1].version == '2.1.0'  # highest ^2.0.0
    
    # Generate lockfile JSON
    lockfile_json = resolution.to_lockfile().to_json()
    lockfile_data = json.loads(lockfile_json)
    assert lockfile_data['version'] == 1
    assert len(lockfile_data['packages']) == 3
    
    # Verify lockfile roundtrip
    lockfile2 = pkg.Lockfile.from_json(lockfile_json)
    assert len(lockfile2.packages) == 3


def test_lockfile_checksum_verification() -> None:
    """Test that lockfile entries include checksums for integrity verification"""
    registry = {
        'app': {'1.0.0': {'name': 'app', 'version': '1.0.0', 'dependencies': {}}},
    }
    specs = [pkg.PackageSpec('app', '1.0.0', {})]
    resolution = pkg.resolve_versions(specs, registry)
    
    assert resolution.packages[0].checksum is not None
    assert resolution.packages[0].checksum.startswith('sha256:') or len(resolution.packages[0].checksum) >= 32


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])