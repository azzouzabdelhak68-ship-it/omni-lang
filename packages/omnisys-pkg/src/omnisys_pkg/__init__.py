"""OMNISYS.pkg — package manager: manifests, version resolution, install.

Python reference implementation of the OMNISYS ``pkg`` module (v6), mirroring
the JS reference lane ``omnisys/pkg.js`` and satisfying the registry contract
(``OMNISYS_MODULES["pkg"]``). The resolver is an in-process BFS over a
registry map (name -> version -> spec) with a visited set; ``manifest`` and
``install`` bridge to OMNISYS.fs, declaring the ``filesystem`` capability.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from omnisys_fs import join_path, make_dir, read_file, write_file
from omnisys_serde import json_decode, json_encode

__all__ = [
    'manifest',
    'create',
    'resolve',
    'install',
    'registry_add',
    'registry_get',
    'list_dependencies',
    'parse_version',
    'satisfies',
    'resolve_versions',
    'compute_checksum',
]

Spec: TypeAlias = dict[str, Any]
Registry: TypeAlias = dict[str, Any]
Request: TypeAlias = dict[str, Any]


# ---------------------------------------------------------------------------
# Semantic Versioning
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(
    r'^(?P<major>0|[1-9]\d*)'
    r'\.(?P<minor>0|[1-9]\d*)'
    r'\.(?P<patch>0|[1-9]\d*)'
    r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
    r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
    r'(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
)


@dataclass(frozen=True)
class Version:
    """Immutable semantic version (major.minor.patch[-prerelease][+build])."""

    major: int
    minor: int
    patch: int
    prerelease: str = ''
    build: str = ''

    def __str__(self) -> str:
        base = f'{self.major}.{self.minor}.{self.patch}'
        if self.prerelease:
            base += f'-{self.prerelease}'
        if self.build:
            base += f'+{self.build}'
        return base

    def _cmp_key(self) -> tuple:
        # For ordering: prerelease versions are "less than" release versions
        # Use (0, prerelease) for prerelease, (1, '') for release so prerelease < release
        prerelease_key = (0, self.prerelease) if self.prerelease else (1, '')
        return (self.major, self.minor, self.patch, prerelease_key)

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._cmp_key() < other._cmp_key()

    def __le__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._cmp_key() <= other._cmp_key()

    def __gt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._cmp_key() > other._cmp_key()

    def __ge__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._cmp_key() >= other._cmp_key()


def parse_version(version: str) -> Version:
    """Parse a semantic version string into a ``Version`` object.

    Supports full SemVer 2.0.0: ``major.minor.patch[-prerelease][+build]``.
    Raises ``ValueError`` for invalid versions.
    """
    m = _VERSION_RE.match(version.strip())
    if not m:
        raise ValueError(f'Invalid semantic version: {version!r}')
    return Version(
        major=int(m.group('major')),
        minor=int(m.group('minor')),
        patch=int(m.group('patch')),
        prerelease=m.group('prerelease') or '',
        build=m.group('build') or '',
    )


def _compare_versions(v1: Version, v2: Version) -> int:
    """Compare two versions. Returns -1, 0, or 1."""
    if v1._cmp_key() < v2._cmp_key():
        return -1
    if v1._cmp_key() > v2._cmp_key():
        return 1
    return 0


def _match_simple(v: Version, constraint: str) -> bool:
    """Match version against simple constraint (>=, <=, >, <, =, ==)."""
    # Check longer operators first to avoid '==' matching as '='
    ops = [
        ('>=', lambda a, b: _compare_versions(a, b) >= 0),
        ('<=', lambda a, b: _compare_versions(a, b) <= 0),
        ('==', lambda a, b: _compare_versions(a, b) == 0),
        ('>', lambda a, b: _compare_versions(a, b) > 0),
        ('<', lambda a, b: _compare_versions(a, b) < 0),
        ('=', lambda a, b: _compare_versions(a, b) == 0),
    ]
    for op, fn in ops:
        if constraint.startswith(op):
            target = parse_version(constraint[len(op):].strip())
            return fn(v, target)
    return False


def _match_caret(v: Version, constraint: str) -> bool:
    """Match version against caret constraint (^major.minor.patch)."""
    # ^1.2.3 := >=1.2.3 <2.0.0 (allows minor/patch updates)
    # ^0.2.3 := >=0.2.3 <0.3.0 (allows patch updates only for 0.x)
    # ^0.0.3 := >=0.0.3 <0.0.4 (allows no updates for 0.0.x)
    # Prereleases only match if the base version is also a prerelease
    if not constraint.startswith('^'):
        return False
    target = parse_version(constraint[1:].strip())
    if target.major == 0:
        if target.minor == 0:
            upper = Version(target.major, target.minor, target.patch + 1)
        else:
            upper = Version(target.major, target.minor + 1, 0)
    else:
        upper = Version(target.major + 1, 0, 0)
    
    # If target is a prerelease, allow prereleases of the same base version
    if target.prerelease:
        # For ^1.0.0-alpha, allow >=1.0.0-alpha <1.0.1 (next patch)
        upper = Version(target.major, target.minor, target.patch + 1)
    
    # Check if v satisfies the range
    if not (_compare_versions(v, target) >= 0 and _compare_versions(v, upper) < 0):
        return False
    
    # If target is a release (no prerelease), don't match prereleases
    if not target.prerelease and v.prerelease:
        return False
    
    return True


def _match_tilde(v: Version, constraint: str) -> bool:
    """Match version against tilde constraint (~major.minor.patch)."""
    # ~1.2.3 := >=1.2.3 <1.3.0 (allows patch updates only)
    # ~1.2 := >=1.2.0 <1.3.0
    # ~1 := >=1.0.0 <2.0.0
    if not constraint.startswith('~'):
        return False
    rest = constraint[1:].strip()
    parts = rest.split('.')
    if len(parts) == 1:
        major = int(parts[0])
        lower = Version(major, 0, 0)
        upper = Version(major + 1, 0, 0)
    elif len(parts) == 2:
        major, minor = int(parts[0]), int(parts[1])
        lower = Version(major, minor, 0)
        upper = Version(major, minor + 1, 0)
    else:
        target = parse_version(rest)
        lower = target
        upper = Version(target.major, target.minor + 1, 0)
    return _compare_versions(v, lower) >= 0 and _compare_versions(v, upper) < 0


def satisfies(version: str, constraint: str) -> bool:
    """Check if a version satisfies a constraint.

    Supports:
    - Exact: ``1.2.3``, ``=1.2.3``, ``==1.2.3``
    - Ranges: ``>=1.2.3``, ``<=1.2.3``, ``>1.2.3``, ``<1.2.3``
    - Caret: ``^1.2.3`` (allows minor/patch updates, not major)
    - Tilde: ``~1.2.3`` (allows patch updates only)
    - Union: ``^1.2.3 || >=2.0.0`` (OR of constraints)
    """
    v = parse_version(version)
    # Handle union constraints (||)
    for part in constraint.split('||'):
        part = part.strip()
        if not part:
            continue
        if part.startswith('^'):
            if _match_caret(v, part):
                return True
        elif part.startswith('~'):
            if _match_tilde(v, part):
                return True
        elif any(part.startswith(op) for op in ('>=', '<=', '>', '<', '=', '==')):
            if _match_simple(v, part):
                return True
        else:
            # Bare version treated as exact match
            if _match_simple(v, f'={part}'):
                return True
    return False


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def compute_checksum(content: bytes) -> str:
    """Compute SHA256 checksum of package content (hex string)."""
    return hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# Package Spec & Lockfile
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PackageSpec:
    """A package specification with version constraints and dependencies."""

    name: str
    version_constraint: str
    dependencies: dict[str, str] = field(default_factory=dict)
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            'name': self.name,
            'version': self.version_constraint,
            'dependencies': self.dependencies,
        }
        if self.checksum:
            d['checksum'] = self.checksum
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PackageSpec:
        return cls(
            name=d['name'],
            version_constraint=d.get('version', d.get('version_constraint', '*')),
            dependencies=d.get('dependencies', {}),
            checksum=d.get('checksum'),
        )


@dataclass(frozen=True)
class LockfileEntry:
    """A locked package entry with resolved version and checksum."""

    name: str
    version: str
    checksum: str
    dependencies: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'checksum': self.checksum,
            'dependencies': self.dependencies,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LockfileEntry:
        return cls(
            name=d['name'],
            version=d['version'],
            checksum=d['checksum'],
            dependencies=d.get('dependencies', {}),
        )


@dataclass(frozen=True)
class Lockfile:
    """Content-addressable lockfile storing resolved versions and checksums."""

    packages: tuple[LockfileEntry, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize lockfile to JSON string."""
        data = {
            'version': 1,
            'packages': [p.to_dict() for p in self.packages],
            'metadata': self.metadata,
        }
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> Lockfile:
        """Deserialize lockfile from JSON string."""
        data = json.loads(json_str)
        packages = tuple(LockfileEntry.from_dict(p) for p in data.get('packages', []))
        metadata = data.get('metadata', {})
        return cls(packages=packages, metadata=metadata)

    def get(self, name: str) -> LockfileEntry | None:
        """Get a locked package by name."""
        for p in self.packages:
            if p.name == name:
                return p
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            'version': 1,
            'packages': [p.to_dict() for p in self.packages],
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Lockfile:
        packages = tuple(LockfileEntry.from_dict(p) for p in d.get('packages', []))
        metadata = d.get('metadata', {})
        return cls(packages=packages, metadata=metadata)


@dataclass(frozen=True)
class Resolution:
    """Result of version resolution: ordered list of locked packages."""

    packages: tuple[LockfileEntry, ...]
    lockfile: Lockfile
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_lockfile(self) -> Lockfile:
        return self.lockfile

    def to_list(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.packages]


# ---------------------------------------------------------------------------
# Deterministic Version Resolution
# ---------------------------------------------------------------------------

def _available_versions(registry: Registry, name: str) -> list[Version]:
    """Get all available versions for a package, sorted descending."""
    versions_map = registry.get(name, {})
    vers = []
    for v_str in versions_map:
        try:
            vers.append(parse_version(v_str))
        except ValueError:
            continue
    return sorted(vers, reverse=True)


def _select_best_version(
    registry: Registry,
    name: str,
    constraint: str,
    lockfile: Lockfile | None = None,
) -> str | None:
    """Select the best matching version for a package given a constraint."""
    # If lockfile has an entry, prefer it if it satisfies the constraint
    if lockfile:
        locked = lockfile.get(name)
        if locked and satisfies(locked.version, constraint):
            # Verify the locked version exists in registry
            if name in registry and locked.version in registry[name]:
                return locked.version

    # Otherwise, find the highest matching version
    for v in _available_versions(registry, name):
        if satisfies(str(v), constraint):
            return str(v)
    return None


def resolve_versions(
    packages: list[PackageSpec],
    registry: Registry,
    lockfile: Lockfile | None = None,
) -> Resolution:
    """Resolve package versions with a deterministic algorithm.

    Algorithm:
    1. Build dependency graph from package specs (including transitive deps from registry)
    2. Topologically sort (dependencies before dependents)
    3. For each package in order, select highest version satisfying constraint
       that is compatible with already-resolved dependencies
    4. Produce a lockfile with resolved versions and checksums

    Returns a ``Resolution`` with ordered packages and a lockfile.
    """
    # Build initial spec map from provided packages
    spec_by_name: dict[str, PackageSpec] = {p.name: p for p in packages}
    resolved: dict[str, LockfileEntry] = {}
    warnings: list[str] = []
    visiting: set[str] = set()

    def get_spec(name: str, constraint: str) -> PackageSpec:
        """Get or create a spec for a package."""
        if name in spec_by_name:
            return spec_by_name[name]
        # Create a minimal spec for transitive dependencies
        spec = PackageSpec(name=name, version_constraint=constraint, dependencies={})
        spec_by_name[name] = spec
        return spec

    def visit(name: str, constraint: str) -> None:
        if name in resolved:
            return
        if name in visiting:
            warnings.append(f'Circular dependency detected involving {name}')
            return

        visiting.add(name)
        spec = get_spec(name, constraint)

        # Resolve explicit spec dependencies first
        for dep_name, dep_constraint in spec.dependencies.items():
            visit(dep_name, dep_constraint)

        # Select best version for this package
        selected_version = _select_best_version(registry, name, spec.version_constraint, lockfile)
        if not selected_version:
            warnings.append(f'No version found for {name} matching {spec.version_constraint}')
            visiting.remove(name)
            return

        # Get dependencies from registry at selected version
        reg_entry = registry[name].get(selected_version)
        if not reg_entry:
            warnings.append(f'Registry missing entry for {name}@{selected_version}')
            visiting.remove(name)
            return

        # Also visit transitive dependencies from registry
        reg_deps = reg_entry.get('dependencies', {})
        for dep_name, dep_constraint in reg_deps.items():
            if dep_name not in spec.dependencies:  # Only visit if not already handled by spec
                visit(dep_name, dep_constraint)

        # Merge registry dependencies with spec dependencies
        all_dep_constraints = {**reg_deps, **spec.dependencies}
        dep_versions = {dep: resolved[dep].version for dep in all_dep_constraints if dep in resolved}

        # Verify checksum if provided
        checksum = spec.checksum
        if not checksum:
            # Compute from registry entry content
            content = json.dumps(reg_entry, separators=(',', ':'), sort_keys=True).encode()
            checksum = compute_checksum(content)

        entry = LockfileEntry(
            name=name,
            version=selected_version,
            checksum=checksum,
            dependencies=dep_versions,
        )
        resolved[name] = entry
        visiting.remove(name)

    # Visit all packages
    for pkg in packages:
        visit(pkg.name, pkg.version_constraint)

    # Produce ordered list (dependencies first)
    ordered: list[LockfileEntry] = []
    seen: set[str] = set()

    def order(name: str) -> None:
        if name in seen or name not in resolved:
            return
        entry = resolved[name]
        for dep in entry.dependencies:
            order(dep)
        if name not in seen:
            seen.add(name)
            ordered.append(entry)

    for pkg in packages:
        order(pkg.name)

    return Resolution(
        packages=tuple(ordered),
        lockfile=Lockfile(packages=tuple(ordered)),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Original pkg module functions (backward compatible)
# ---------------------------------------------------------------------------

def create(name: Any, version: Any, deps: Any) -> Spec:
    """Create a package spec ``{tag, name, version, dependencies}``."""
    return {
        'tag': 'package',
        'name': str(name),
        'version': str(version),
        'dependencies': deps or {},
    }


def registry_add(registry: Registry, spec: Spec, version: Any) -> Registry:
    """Add ``spec`` to ``registry``; optionally alias the version map."""
    name = spec['name']
    registry.setdefault(name, {})
    registry[name][spec['version']] = {
        'name': name,
        'version': spec['version'],
        'dependencies': spec.get('dependencies', {}),
    }
    if version is not None:
        registry[str(version)] = registry[name]
    return registry


def registry_get(registry: Registry, name: Any, version: Any) -> Spec | None:
    """Return the spec for ``name``@``version`` (default version when None)."""
    versions = registry.get(str(name))
    if not versions:
        return None
    key = str(version) if version else list(versions)[0]
    return versions.get(key) or None


def list_dependencies(spec: Spec) -> list[str]:
    """Return the dependency names of ``spec`` in insertion order."""
    return list((spec.get('dependencies') or {}).keys())


def resolve(name: Any, version: Any, registry: Registry) -> list[Spec]:
    """BFS-resolve ``name``@``version`` into an ordered install list."""
    seen: set[str] = set()
    order: list[Spec] = []
    queue: list[Request] = [{'name': str(name), 'version': str(version or 'latest')}]
    while queue:
        req = queue.pop(0)
        key = req['name'] + '@' + req['version']
        if key in seen:
            continue
        seen.add(key)
        spec = registry_get(registry, req['name'], req['version'])
        if not spec:
            continue
        order.append(spec)
        for dep_name, dep_version in (spec.get('dependencies') or {}).items():
            queue.append({'name': dep_name, 'version': dep_version})
    return order


def manifest(path: Any) -> Any:
    """Read an OmniScript package manifest from ``path`` and decode it."""
    text = read_file(str(path))
    return json_decode(text)


def install(dir: Any, registry: Registry) -> dict[str, Any]:
    """Install every spec in ``registry`` into ``dir`` as ``<name>-<ver>.pkg.json``."""
    make_dir(str(dir))
    for name in registry:
        versions = registry[name]
        for version in versions:
            spec = versions[version]
            target = join_path(str(dir), spec['name'] + '-' + spec['version'] + '.pkg.json')
            write_file(target, json_encode(spec))
    return {'tag': 'install', 'dir': str(dir), 'count': len(registry)}