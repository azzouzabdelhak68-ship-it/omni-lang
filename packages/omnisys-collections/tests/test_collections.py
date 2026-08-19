# ruff: noqa: PLR2004, Q000
"""Unit tests for every OMNISYS.collections function."""

import importlib

import omnisys_collections as c
import omnisys_core
import pytest
from omnisys_core import PanicError


def _deque() -> dict[str, object]:
    return {'tag': 'deque', 'items': []}


def _heap() -> dict[str, object]:
    return {'tag': 'heap', 'items': []}


def test_list_push_appends_and_returns_same_list() -> None:
    xs: list[int] = [1, 2]
    assert c.list_push(xs, 3) is xs
    assert xs == [1, 2, 3]


def test_list_pop_returns_last_item() -> None:
    xs = [1, 2, 3]
    assert c.list_pop(xs) == 3
    assert xs == [1, 2]


def test_list_pop_on_empty_list_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_pop on empty list'):
        c.list_pop([])


def test_list_get_returns_item() -> None:
    assert c.list_get([10, 20, 30], 1) == 20


def test_list_get_negative_index_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_get index out of range'):
        c.list_get([10, 20], -1)


def test_list_get_past_end_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_get index out of range'):
        c.list_get([10, 20], 2)


def test_list_set_replaces_and_returns_same_list() -> None:
    xs = [1, 2, 3]
    assert c.list_set(xs, 1, 99) is xs
    assert xs == [1, 99, 3]


def test_list_set_negative_index_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_set index out of range'):
        c.list_set([1, 2], -1, 0)


def test_list_set_past_end_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_set index out of range'):
        c.list_set([1, 2], 2, 0)


def test_list_slice_returns_new_list() -> None:
    xs = [0, 1, 2, 3, 4]
    result = c.list_slice(xs, 1, 4)
    assert result == [1, 2, 3]
    assert result is not xs


def test_list_append_returns_new_list() -> None:
    a = [1, 2]
    b = [3, 4]
    result = c.list_append(a, b)
    assert result == [1, 2, 3, 4]
    assert result is not a
    assert a == [1, 2]


def test_list_contains_true() -> None:
    assert c.list_contains([1, 2, 3], 2)


def test_list_contains_false() -> None:
    assert not c.list_contains([1, 2, 3], 9)


def test_list_index_of_found() -> None:
    assert c.list_index_of(['a', 'b', 'c'], 'b') == 1


def test_list_index_of_absent_returns_minus_one() -> None:
    assert c.list_index_of(['a', 'b'], 'z') == -1


def test_list_remove_removes_and_returns_same_list() -> None:
    xs = [1, 2, 3, 4]
    assert c.list_remove(xs, 2) is xs
    assert xs == [1, 2, 4]


def test_list_remove_negative_index_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_remove index out of range'):
        c.list_remove([1, 2], -1)


def test_list_remove_past_end_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.list_remove index out of range'):
        c.list_remove([1, 2], 2)


def test_list_sort_returns_new_sorted_list() -> None:
    xs = [3, 1, 2]
    result = c.list_sort(xs)
    assert result == [1, 2, 3]
    assert result is not xs
    assert xs == [3, 1, 2]


def test_list_reverse_returns_new_reversed_list() -> None:
    xs = [1, 2, 3]
    result = c.list_reverse(xs)
    assert result == [3, 2, 1]
    assert result is not xs
    assert xs == [1, 2, 3]


def test_list_fold_reduces_left_to_right() -> None:
    assert c.list_fold([1, 2, 3, 4], lambda acc, item: acc + item, 0) == 10


def test_list_fold_with_init_type_change() -> None:
    assert c.list_fold([1, 2, 3], lambda acc, item: str(acc) + str(item), '') == '123'


def test_list_map_applies_fn() -> None:
    assert c.list_map([1, 2, 3], lambda x: x * x) == [1, 4, 9]


def test_list_filter_keeps_truthy() -> None:
    assert c.list_filter([1, 0, 2, 0, 3], lambda x: x != 0) == [1, 2, 3]


def test_list_filter_uses_truthiness() -> None:
    assert c.list_filter([0, 1, '', 'x', None, []], bool) == [1, 'x']


def test_list_join_joins_string_forms() -> None:
    assert c.list_join([1, 2, 3], '-') == '1-2-3'


def test_list_join_empty() -> None:
    assert c.list_join([], ',') == ''


def test_list_zip_pairs_up_to_min_length() -> None:
    assert c.list_zip([1, 2, 3], ['a', 'b']) == [[1, 'a'], [2, 'b']]


def test_list_zip_empty_first() -> None:
    assert c.list_zip([], [1, 2]) == []


def test_map_get_existing_key() -> None:
    assert c.map_get({'a': 1, 'b': 2}, 'b') == 2


def test_map_get_missing_key_raises() -> None:
    with pytest.raises(KeyError):
        c.map_get({'a': 1}, 'zz')


def test_map_set_sets_and_returns_same_map() -> None:
    m: dict[str, int] = {'a': 1}
    assert c.map_set(m, 'b', 2) is m
    assert m == {'a': 1, 'b': 2}


def test_map_set_overwrites() -> None:
    m = {'a': 1}
    c.map_set(m, 'a', 9)
    assert m == {'a': 9}


def test_map_remove_deletes_existing_key() -> None:
    m = {'a': 1, 'b': 2}
    assert c.map_remove(m, 'a') is m
    assert m == {'b': 2}


def test_map_remove_absent_key_is_noop() -> None:
    m = {'a': 1}
    assert c.map_remove(m, 'zz') is m
    assert m == {'a': 1}


def test_map_has_present_key() -> None:
    assert c.map_has({'a': 1}, 'a')


def test_map_has_absent_key() -> None:
    assert not c.map_has({'a': 1}, 'b')


def test_map_keys_insertion_order() -> None:
    assert c.map_keys({'a': 1, 'b': 2, 'c': 3}) == ['a', 'b', 'c']


def test_map_values_insertion_order() -> None:
    assert c.map_values({'a': 1, 'b': 2, 'c': 3}) == [1, 2, 3]


def test_map_size_counts_entries() -> None:
    assert c.map_size({'a': 1, 'b': 2}) == 2


def test_set_add_appends_new_item() -> None:
    s: list[int] = [1]
    assert c.set_add(s, 2) is s
    assert s == [1, 2]


def test_set_add_skips_duplicate() -> None:
    s = [1, 2]
    c.set_add(s, 1)
    assert s == [1, 2]


def test_set_remove_removes_item() -> None:
    s = [1, 2, 3]
    assert c.set_remove(s, 2) is s
    assert s == [1, 3]


def test_set_remove_absent_item_is_noop() -> None:
    s = [1, 2]
    c.set_remove(s, 9)
    assert s == [1, 2]


def test_set_has_present_item() -> None:
    assert c.set_has([1, 2], 2)


def test_set_has_absent_item() -> None:
    assert not c.set_has([1, 2], 3)


def test_set_size_counts_items() -> None:
    assert c.set_size([1, 2, 3]) == 3


def test_set_union_combines_unique_items() -> None:
    result = c.set_union([1, 2], [2, 3])
    assert result == [1, 2, 3]
    assert result is not None


def test_set_union_keeps_a_order_and_appends_b() -> None:
    assert c.set_union([3, 1], [2, 3, 4]) == [3, 1, 2, 4]


def test_set_union_does_not_mutate_inputs() -> None:
    a = [1, 2]
    b = [2, 3]
    c.set_union(a, b)
    assert a == [1, 2]
    assert b == [2, 3]


def test_set_intersection_keeps_a_items_in_b() -> None:
    assert c.set_intersection([1, 2, 3], [2, 3, 4]) == [2, 3]


def test_set_intersection_disjoint() -> None:
    assert c.set_intersection([1, 2], [3, 4]) == []


def test_set_difference_keeps_a_items_not_in_b() -> None:
    assert c.set_difference([1, 2, 3], [2, 4]) == [1, 3]


def test_set_difference_full_overlap() -> None:
    assert c.set_difference([1, 2], [1, 2]) == []


def test_deque_push_front_inserts() -> None:
    d = _deque()
    assert c.deque_push_front(d, 1) is d
    assert d['items'] == [1]
    c.deque_push_front(d, 2)
    assert d['items'] == [2, 1]


def test_deque_push_back_appends() -> None:
    d = _deque()
    assert c.deque_push_back(d, 1) is d
    c.deque_push_back(d, 2)
    assert d['items'] == [1, 2]


def test_deque_pop_front_returns_front() -> None:
    d = _deque()
    c.deque_push_back(d, 1)
    c.deque_push_back(d, 2)
    assert c.deque_pop_front(d) == 1
    assert d['items'] == [2]


def test_deque_pop_front_on_empty_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.deque_pop_front on empty deque'):
        c.deque_pop_front(_deque())


def test_deque_pop_back_returns_back() -> None:
    d = _deque()
    c.deque_push_back(d, 1)
    c.deque_push_back(d, 2)
    assert c.deque_pop_back(d) == 2
    assert d['items'] == [1]


def test_deque_pop_back_on_empty_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.deque_pop_back on empty deque'):
        c.deque_pop_back(_deque())


def test_deque_size_counts_items() -> None:
    d = _deque()
    c.deque_push_back(d, 1)
    c.deque_push_back(d, 2)
    c.deque_push_front(d, 0)
    assert c.deque_size(d) == 3


def test_heap_push_single_item() -> None:
    h = _heap()
    assert c.heap_push(h, 5) is h
    assert h['items'] == [5]


def test_heap_push_sifts_up() -> None:
    h = _heap()
    c.heap_push(h, 5)
    c.heap_push(h, 3)
    c.heap_push(h, 4)
    assert h['items'] == [3, 5, 4]


def test_heap_push_keeps_smallest_first_when_no_swap_needed() -> None:
    h = _heap()
    c.heap_push(h, 2)
    c.heap_push(h, 3)
    c.heap_push(h, 4)
    assert h['items'] == [2, 3, 4]


def test_heap_pop_returns_minimum() -> None:
    h = _heap()
    for x in [5, 3, 8, 1, 9]:
        c.heap_push(h, x)
    assert c.heap_pop(h) == 1


def test_heap_pop_sifts_down_left() -> None:
    h = _heap()
    for x in [2, 3, 4, 5]:
        c.heap_push(h, x)
    assert c.heap_pop(h) == 2
    assert c.heap_peek(h) == 3


def test_heap_pop_sifts_down_right() -> None:
    h = _heap()
    for x in [2, 4, 3, 5]:
        c.heap_push(h, x)
    assert c.heap_pop(h) == 2
    assert c.heap_peek(h) == 3


def test_heap_pop_single_element() -> None:
    h = _heap()
    c.heap_push(h, 42)
    assert c.heap_pop(h) == 42
    assert c.heap_size(h) == 0


def test_heap_pop_on_empty_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.heap_pop on empty heap'):
        c.heap_pop(_heap())


def test_heap_peek_returns_minimum_without_removing() -> None:
    h = _heap()
    c.heap_push(h, 7)
    c.heap_push(h, 2)
    assert c.heap_peek(h) == 2
    assert c.heap_size(h) == 2


def test_heap_peek_on_empty_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.heap_peek on empty heap'):
        c.heap_peek(_heap())


def test_heap_size_counts_items() -> None:
    h = _heap()
    c.heap_push(h, 1)
    c.heap_push(h, 2)
    assert c.heap_size(h) == 2


def test_ring_new_builds_empty_ring() -> None:
    r = c.ring_new(3)
    assert r == {'tag': 'ring', 'capacity': 3, 'items': []}


def test_ring_push_appends_until_capacity() -> None:
    r = c.ring_new(2)
    assert c.ring_push(r, 1) is r
    c.ring_push(r, 2)
    assert r['items'] == [1, 2]


def test_ring_push_evicts_front_over_capacity() -> None:
    r = c.ring_new(2)
    c.ring_push(r, 1)
    c.ring_push(r, 2)
    c.ring_push(r, 3)
    assert r['items'] == [2, 3]


def test_ring_pop_returns_front() -> None:
    r = c.ring_new(3)
    c.ring_push(r, 1)
    c.ring_push(r, 2)
    assert c.ring_pop(r) == 1
    assert r['items'] == [2]


def test_ring_pop_on_empty_panics() -> None:
    with pytest.raises(PanicError, match=r'collections\.ring_pop on empty ring'):
        c.ring_pop(c.ring_new(2))


def test_ring_size_counts_items() -> None:
    r = c.ring_new(4)
    c.ring_push(r, 1)
    c.ring_push(r, 2)
    assert c.ring_size(r) == 2


def test_ring_size_never_exceeds_capacity() -> None:
    r = c.ring_new(2)
    for i in range(10):
        c.ring_push(r, i)
    assert c.ring_size(r) == 2


def test_panic_resolves_existing_core_panic(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(omnisys_core, 'panic', seen.append, raising=False)
    importlib.reload(c)
    try:
        c.panic('collections.probe')
        assert seen == ['collections.probe']
    finally:
        monkeypatch.undo()
        importlib.reload(c)
