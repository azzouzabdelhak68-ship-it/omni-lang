"""OMNISYS.fs — filesystem access and path helpers.

Python reference implementation of the OMNISYS.fs module, mirroring the JS lane
(``omnisys/fs.js``) as locked by the compiler registry (``OMNISYS_MODULES["fs"]``).
The eleven I/O functions declare the ``filesystem`` capability; the three path
helpers are pure. stdlib only (``shutil``, ``pathlib``).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import NoReturn

__all__ = [
    'read_file',
    'write_file',
    'append_file',
    'delete_file',
    'file_exists',
    'file_size',
    'list_dir',
    'make_dir',
    'remove_dir',
    'rename_file',
    'copy_file',
    'join_path',
    'basename',
    'dirname',
]

_PathLike = str | Path


def _panic(message: str) -> NoReturn:
    """Abort with ``message``, mirroring ``omnisys.core.panic``."""
    raise TypeError(message)


def _as_path(path: _PathLike, fn: str) -> Path:
    """Coerce ``path`` to a ``Path``, panicking when it is not path-like."""
    if isinstance(path, Path):
        return path
    if isinstance(path, str):
        return Path(path)
    _panic(f'{fn}: path must be a str or pathlib.Path')


def read_file(path: _PathLike) -> str:
    """Read the UTF-8 text of the file at ``path``, raising on failure."""
    p = _as_path(path, 'read_file')
    with p.open('r', encoding='utf-8', newline='') as handle:
        return handle.read()


def write_file(path: _PathLike, text: str) -> str:
    """Write ``text`` as UTF-8 to the file at ``path``, returning the path."""
    p = _as_path(path, 'write_file')
    p.write_text(text, encoding='utf-8', newline='')
    return str(p)


def append_file(path: _PathLike, text: str) -> str:
    """Append ``text`` as UTF-8 to the file at ``path``, returning the path."""
    p = _as_path(path, 'append_file')
    with p.open('a', encoding='utf-8', newline='') as handle:
        handle.write(text)
    return str(p)


def delete_file(path: _PathLike) -> bool:
    """Delete the file at ``path``, returning False when deletion fails."""
    try:
        _as_path(path, 'delete_file').unlink()
    except OSError:
        return False
    return True


def file_exists(path: _PathLike) -> bool:
    """Return whether a file or directory exists at ``path``."""
    return _as_path(path, 'file_exists').exists()


def file_size(path: _PathLike) -> int:
    """Return the size in bytes of the file at ``path``, or -1 on failure."""
    try:
        return _as_path(path, 'file_size').stat().st_size
    except OSError:
        return -1


def list_dir(path: _PathLike) -> list[str]:
    """List the entry names in the directory at ``path``, sorted."""
    return sorted(entry.name for entry in _as_path(path, 'list_dir').iterdir())


def make_dir(path: _PathLike) -> bool:
    """Create the directory at ``path``, including parents, as needed."""
    try:
        _as_path(path, 'make_dir').mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return True


def remove_dir(path: _PathLike) -> bool:
    """Remove the directory tree at ``path``, if present."""
    try:
        shutil.rmtree(_as_path(path, 'remove_dir'), ignore_errors=True)
    except OSError:
        return False
    return True


def rename_file(old_path: _PathLike, new_path: _PathLike) -> bool:
    """Rename the file or directory at ``old_path`` to ``new_path``."""
    try:
        _as_path(old_path, 'rename_file').rename(_as_path(new_path, 'rename_file'))
    except OSError:
        return False
    return True


def copy_file(src: _PathLike, dst: _PathLike) -> bool:
    """Copy the file at ``src`` to ``dst``, preserving metadata."""
    try:
        shutil.copy2(_as_path(src, 'copy_file'), _as_path(dst, 'copy_file'))
    except OSError:
        return False
    return True


def join_path(a: _PathLike, b: _PathLike) -> str:
    """Join the path components ``a`` and ``b``, returning the combined path."""
    return str(_as_path(a, 'join_path').joinpath(_as_path(b, 'join_path')))


def basename(path: _PathLike) -> str:
    """Return the final component of ``path``."""
    return _as_path(path, 'basename').name


def dirname(path: _PathLike) -> str:
    """Return the parent directory of ``path``."""
    return str(_as_path(path, 'dirname').parent)
