"""Hypothesis property tests for OMNISYS.fs invariants."""

import string
from pathlib import Path

import omnisys_fs as fs
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

_COMPONENT = st.text(
    alphabet=string.ascii_lowercase + string.digits + '_-',
    min_size=1,
    max_size=16,
)
_TEXT = st.text(max_size=256)
_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@given(st.lists(_COMPONENT, min_size=1, max_size=5))
@_SETTINGS
def test_basename_idempotent(parts: list[str]) -> None:
    path = '/'.join(parts)
    assert fs.basename(fs.basename(path)) == fs.basename(path)


@given(_COMPONENT, _COMPONENT)
@_SETTINGS
def test_join_basename_dirname_invariants(head: str, tail: str) -> None:
    joined = fs.join_path(head, tail)
    assert fs.basename(joined) == tail
    assert fs.dirname(joined) == head


@given(_TEXT)
@_SETTINGS
def test_write_read_roundtrip_preserves_text(tmp_path: Path, text: str) -> None:
    target = tmp_path / 'data.txt'
    fs.write_file(target, text)
    assert fs.read_file(target) == text
    assert fs.file_size(target) == len(text.encode('utf-8'))


@given(_TEXT)
@_SETTINGS
def test_copy_file_preserves_bytes(tmp_path: Path, text: str) -> None:
    src = tmp_path / 'src.txt'
    dst = tmp_path / 'dst.txt'
    fs.write_file(src, text)
    assert fs.copy_file(src, dst) is True
    assert fs.read_file(dst) == text
    assert fs.file_size(src) == fs.file_size(dst)


@given(_TEXT)
@_SETTINGS
def test_rename_preserves_content(tmp_path: Path, text: str) -> None:
    src = tmp_path / 'src.txt'
    dst = tmp_path / 'dst.txt'
    if fs.file_exists(dst):
        fs.delete_file(dst)
    fs.write_file(src, text)
    assert fs.rename_file(src, dst) is True
    assert fs.file_exists(src) is False
    assert fs.read_file(dst) == text


@given(_TEXT)
@_SETTINGS
def test_append_preserves_content(tmp_path: Path, text: str) -> None:
    target = tmp_path / 'log.txt'
    fs.write_file(target, 'prefix')
    fs.append_file(target, text)
    assert fs.read_file(target) == 'prefix' + text
