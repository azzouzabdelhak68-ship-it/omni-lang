"""Unit tests for every OMNISYS.fs function (all writes under ``tmp_path``)."""

from pathlib import Path, PurePath

import omnisys_fs as fs
import pytest


def test_write_read_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / 'roundtrip.txt'
    assert fs.write_file(target, 'hello world') == str(target)
    assert fs.read_file(target) == 'hello world'


def test_write_read_roundtrip_str_path(tmp_path: Path) -> None:
    target = tmp_path / 'strpath.txt'
    assert fs.write_file(str(target), 'by string') == str(target)
    assert fs.read_file(str(target)) == 'by string'


def test_write_missing_parent_raises(tmp_path: Path) -> None:
    target = tmp_path / 'no' / 'such' / 'dir' / 'f.txt'
    with pytest.raises(OSError):
        fs.write_file(target, 'x')


def test_read_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        fs.read_file(tmp_path / 'nope.txt')


def test_append_accumulates(tmp_path: Path) -> None:
    target = tmp_path / 'log.txt'
    fs.write_file(target, 'a')
    assert fs.append_file(target, 'b') == str(target)
    fs.append_file(target, 'c')
    assert fs.read_file(target) == 'abc'


def test_append_creates_missing_file(tmp_path: Path) -> None:
    target = tmp_path / 'fresh.txt'
    fs.append_file(target, 'new')
    assert fs.read_file(target) == 'new'


def test_delete_file_removes(tmp_path: Path) -> None:
    target = tmp_path / 'gone.txt'
    fs.write_file(target, 'x')
    assert fs.delete_file(target) is True
    assert fs.file_exists(target) is False


def test_delete_file_missing_returns_false(tmp_path: Path) -> None:
    assert fs.delete_file(tmp_path / 'never.txt') is False


def test_delete_file_directory_returns_false(tmp_path: Path) -> None:
    sub = tmp_path / 'sub'
    sub.mkdir()
    assert fs.delete_file(sub) is False
    assert sub.is_dir()


def test_file_exists_true_and_false(tmp_path: Path) -> None:
    target = tmp_path / 'present.txt'
    assert fs.file_exists(target) is False
    fs.write_file(target, 'x')
    assert fs.file_exists(target) is True
    assert fs.file_exists(tmp_path) is True


def test_file_size_correct(tmp_path: Path) -> None:
    payload = '12345'
    target = tmp_path / 'sized.txt'
    fs.write_file(target, payload)
    assert fs.file_size(target) == len(payload)


def test_file_size_missing_returns_negative_one(tmp_path: Path) -> None:
    assert fs.file_size(tmp_path / 'missing.txt') == -1


def test_list_dir_sorted_with_files_and_dirs(tmp_path: Path) -> None:
    fs.write_file(tmp_path / 'b.txt', 'b')
    fs.write_file(tmp_path / 'a.txt', 'a')
    fs.make_dir(tmp_path / 'sub')
    fs.write_file(tmp_path / 'sub' / 'inner.txt', 'i')
    assert fs.list_dir(tmp_path) == ['a.txt', 'b.txt', 'sub']


def test_list_dir_empty(tmp_path: Path) -> None:
    assert fs.list_dir(tmp_path) == []


def test_list_dir_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        fs.list_dir(tmp_path / 'nope')


def test_make_dir_nested(tmp_path: Path) -> None:
    target = tmp_path / 'a' / 'b' / 'c'
    assert fs.make_dir(target) is True
    assert target.is_dir()


def test_make_dir_existing_returns_true(tmp_path: Path) -> None:
    target = tmp_path / 'exists'
    target.mkdir()
    assert fs.make_dir(target) is True


def test_make_dir_on_file_returns_false(tmp_path: Path) -> None:
    blocker = tmp_path / 'blocker'
    fs.write_file(blocker, 'x')
    assert fs.make_dir(blocker) is False


def test_remove_dir_removes_tree(tmp_path: Path) -> None:
    tree = tmp_path / 'tree'
    fs.make_dir(tree / 'nested')
    fs.write_file(tree / 'top.txt', 't')
    fs.write_file(tree / 'nested' / 'inner.txt', 'i')
    assert fs.remove_dir(tree) is True
    assert tree.exists() is False


def test_remove_dir_missing_returns_true(tmp_path: Path) -> None:
    assert fs.remove_dir(tmp_path / 'ghost') is True


def test_remove_dir_error_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError('boom')

    monkeypatch.setattr('shutil.rmtree', boom)
    assert fs.remove_dir(tmp_path / 'x') is False


def test_rename_file_moves(tmp_path: Path) -> None:
    src = tmp_path / 'a.txt'
    dst = tmp_path / 'b.txt'
    fs.write_file(src, 'payload')
    assert fs.rename_file(src, dst) is True
    assert fs.file_exists(src) is False
    assert fs.read_file(dst) == 'payload'


def test_rename_file_missing_returns_false(tmp_path: Path) -> None:
    assert fs.rename_file(tmp_path / 'no.txt', tmp_path / 'dst.txt') is False


def test_copy_file_copies_content(tmp_path: Path) -> None:
    src = tmp_path / 'a.txt'
    dst = tmp_path / 'b.txt'
    fs.write_file(src, 'copied')
    assert fs.copy_file(src, dst) is True
    assert fs.read_file(dst) == 'copied'


def test_copy_file_missing_returns_false(tmp_path: Path) -> None:
    assert fs.copy_file(tmp_path / 'no.txt', tmp_path / 'dst.txt') is False


def test_join_path_components() -> None:
    assert fs.join_path('a', 'b') == str(PurePath('a', 'b'))
    assert fs.join_path(Path('a'), 'b') == str(PurePath('a', 'b'))
    assert fs.join_path('a/b', 'c') == str(PurePath('a', 'b', 'c'))
    assert fs.join_path('a/', 'b') == str(PurePath('a', 'b'))


def test_basename_various() -> None:
    assert fs.basename('a/b/c.txt') == 'c.txt'
    assert fs.basename('a/b/') == 'b'
    assert fs.basename('single') == 'single'
    assert fs.basename(Path('a/b/c.txt')) == 'c.txt'
    assert fs.basename('') == ''


def test_dirname_various() -> None:
    assert fs.dirname('a/b/c.txt') == str(PurePath('a', 'b'))
    assert fs.dirname('a/b/') == 'a'
    assert fs.dirname(Path('a/b/c.txt')) == str(PurePath('a', 'b'))
    assert fs.dirname('single') == '.'
    assert fs.dirname('') == '.'


def test_panic_on_non_path_argument() -> None:
    with pytest.raises(TypeError):
        fs.read_file(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        fs.join_path('a', 456)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        fs.delete_file(789)  # type: ignore[arg-type]
