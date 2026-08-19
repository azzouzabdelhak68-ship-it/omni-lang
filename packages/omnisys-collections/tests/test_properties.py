# ruff: noqa: Q000
"""Hypothesis property tests for OMNISYS.collections invariants."""

import omnisys_collections as c
from hypothesis import given, settings
from hypothesis import strategies as st

_int_lists = st.lists(st.integers())
_nonempty_int_lists = st.lists(st.integers(), min_size=1)
_int_sets = st.lists(st.integers(), unique=True, min_size=1, max_size=12)
_text_lists = st.lists(st.text())
_pair_lists = st.lists(st.lists(st.integers(), min_size=2, max_size=2))


@st.composite
def _keys_and_values(draw: st.DrawFn) -> tuple[list[int], list[int]]:
    keys = draw(st.lists(st.integers(), unique=True))
    values = draw(st.lists(st.integers(), min_size=len(keys)))
    return keys, values[: len(keys)]


@settings(max_examples=200)
@given(_int_lists)
def test_list_sort_is_idempotent(xs: list[int]) -> None:
    once = c.list_sort(xs)
    assert c.list_sort(once) == once


@settings(max_examples=200)
@given(_int_lists)
def test_list_sort_is_ordered(xs: list[int]) -> None:
    result = c.list_sort(xs)
    assert result == sorted(xs)
    assert all(a <= b for a, b in zip(result, result[1:], strict=False))


@settings(max_examples=200)
@given(_int_lists)
def test_list_sort_does_not_mutate_input(xs: list[int]) -> None:
    snapshot = list(xs)
    c.list_sort(xs)
    assert xs == snapshot


@settings(max_examples=200)
@given(st.lists(st.integers()), st.lists(st.integers()))
def test_list_append_length_is_sum(a: list[int], b: list[int]) -> None:
    assert len(c.list_append(a, b)) == len(a) + len(b)


@settings(max_examples=200)
@given(_int_lists, st.integers(min_value=1, max_value=10))
def test_ring_push_never_exceeds_capacity(xs: list[int], capacity: int) -> None:
    ring = c.ring_new(capacity)
    for item in xs:
        c.ring_push(ring, item)
    assert c.ring_size(ring) <= capacity
    assert len(ring['items']) <= capacity


@settings(max_examples=200)
@given(_nonempty_int_lists)
def test_ring_push_keeps_tail_items(xs: list[int]) -> None:
    capacity = max(1, len(xs) // 2)
    ring = c.ring_new(capacity)
    for item in xs:
        c.ring_push(ring, item)
    assert ring['items'] == xs[-capacity:]


@settings(max_examples=200)
@given(_nonempty_int_lists)
def test_heap_pop_returns_minimum_remaining(xs: list[int]) -> None:
    heap = {'tag': 'heap', 'items': []}
    for item in xs:
        c.heap_push(heap, item)
    previous = c.heap_pop(heap)
    assert previous == min(xs)
    while c.heap_size(heap) > 0:
        current = c.heap_pop(heap)
        assert current >= previous
        previous = current


@settings(max_examples=200)
@given(_nonempty_int_lists)
def test_heap_pop_drains_sorted(xs: list[int]) -> None:
    heap = {'tag': 'heap', 'items': []}
    for item in xs:
        c.heap_push(heap, item)
    popped: list[int] = []
    while c.heap_size(heap) > 0:
        popped.append(c.heap_pop(heap))
    assert popped == sorted(xs)


@settings(max_examples=200)
@given(_int_lists)
def test_heap_size_grows_with_pushes(xs: list[int]) -> None:
    heap = {'tag': 'heap', 'items': []}
    for item in xs:
        c.heap_push(heap, item)
    assert c.heap_size(heap) == len(xs)


@settings(max_examples=200)
@given(_int_sets, _int_sets)
def test_set_union_size_relationship(a: list[int], b: list[int]) -> None:
    union = c.set_union(a, b)
    assert len(union) >= len(a)
    assert len(union) >= len(b)
    assert len(union) == len(set(union))


@settings(max_examples=200)
@given(_int_sets, _int_sets)
def test_set_union_is_unique(a: list[int], b: list[int]) -> None:
    union = c.set_union(a, b)
    assert len(union) == len(set(union))
    for item in a:
        assert item in union
    for item in b:
        assert item in union


@settings(max_examples=200)
@given(_int_sets, _int_sets)
def test_set_intersection_is_subset_of_both(a: list[int], b: list[int]) -> None:
    intersection = c.set_intersection(a, b)
    for item in intersection:
        assert item in a
        assert item in b
    assert len(intersection) == len(set(intersection))


@settings(max_examples=200)
@given(_int_sets, _int_sets)
def test_set_difference_is_subset_of_a(a: list[int], b: list[int]) -> None:
    difference = c.set_difference(a, b)
    for item in difference:
        assert item in a
        assert item not in b
    assert len(difference) == len(set(difference))


@settings(max_examples=200)
@given(_int_lists, _int_lists)
def test_list_zip_length_is_min(a: list[int], b: list[int]) -> None:
    zipped = c.list_zip(a, b)
    assert len(zipped) == min(len(a), len(b))


@settings(max_examples=200)
@given(_int_lists, _int_lists)
def test_list_zip_pairs_align(a: list[int], b: list[int]) -> None:
    zipped = c.list_zip(a, b)
    assert all(pair[0] == a[i] and pair[1] == b[i] for i, pair in enumerate(zipped))


@settings(max_examples=200)
@given(_int_lists)
def test_list_reverse_twice_is_identity(xs: list[int]) -> None:
    assert c.list_reverse(c.list_reverse(xs)) == xs


@settings(max_examples=200)
@given(_int_lists)
def test_list_reverse_does_not_mutate_input(xs: list[int]) -> None:
    snapshot = list(xs)
    c.list_reverse(xs)
    assert xs == snapshot


@settings(max_examples=200)
@given(_int_lists)
def test_list_map_preserves_length(xs: list[int]) -> None:
    assert len(c.list_map(xs, lambda x: x * 2)) == len(xs)


@settings(max_examples=200)
@given(_int_lists)
def test_list_map_is_pointwise(xs: list[int]) -> None:
    assert c.list_map(xs, lambda x: x + 1) == [x + 1 for x in xs]


@settings(max_examples=200)
@given(_int_lists, st.integers(min_value=0, max_value=100))
def test_list_fold_sum_matches_builtin(xs: list[int], init: int) -> None:
    assert c.list_fold(xs, lambda acc, item: acc + item, init) == init + sum(xs)


@settings(max_examples=200)
@given(_int_lists, st.integers(min_value=0, max_value=100))
def test_list_fold_length_via_accumulator(xs: list[int], init: int) -> None:
    assert c.list_fold(xs, lambda acc, item: acc + 1, init) == init + len(xs)


@settings(max_examples=200)
@given(st.lists(st.integers(min_value=0, max_value=10)))
def test_set_add_is_idempotent(xs: list[int]) -> None:
    s: list[int] = []
    for item in xs:
        c.set_add(s, item)
    assert len(s) == len(set(xs))
    assert len(s) == len(set(s))
    snapshot = list(s)
    for item in xs:
        c.set_add(s, item)
    assert s == snapshot


@settings(max_examples=200)
@given(_int_sets, _int_sets)
def test_set_size_is_unique_count(a: list[int], b: list[int]) -> None:
    assert c.set_size(c.set_union(a, b)) == len(set(a) | set(b))
    assert c.set_size(c.set_intersection(a, b)) == len(set(a) & set(b))
    assert c.set_size(c.set_difference(a, b)) == len(set(a) - set(b))


@settings(max_examples=200)
@given(_keys_and_values())
def test_map_set_get_roundtrip(keys_values: tuple[list[int], list[int]]) -> None:
    keys, values = keys_values
    m: dict[int, int] = {}
    for key, value in zip(keys, values, strict=False):
        c.map_set(m, key, value)
    for key, value in zip(keys, values, strict=False):
        assert c.map_get(m, key) == value
    assert c.map_size(m) == len(keys)


@settings(max_examples=200)
@given(st.lists(st.integers(), unique=True))
def test_map_keys_values_sizes(xs: list[int]) -> None:
    m = {i: i * 10 for i in xs}
    assert len(c.map_keys(m)) == len(xs)
    assert len(c.map_values(m)) == len(xs)
    assert c.map_size(m) == len(xs)


@settings(max_examples=200)
@given(_int_lists)
def test_list_contains_matches_in(xs: list[int]) -> None:
    for item in xs:
        assert c.list_contains(xs, item)


@settings(max_examples=200)
@given(st.integers())
def test_list_index_of_single_element(x: int) -> None:
    assert c.list_index_of([x], x) == 0
    assert c.list_index_of([], x) == -1


@settings(max_examples=200)
@given(_text_lists, st.text())
def test_list_join_matches_python_join(xs: list[str], sep: str) -> None:
    assert c.list_join(xs, sep) == sep.join(xs)


@settings(max_examples=200)
@given(_pair_lists)
def test_list_zip_preserves_pair_shapes(pairs: list[list[int]]) -> None:
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    assert c.list_zip(a, b) == pairs


@settings(max_examples=200)
@given(_int_lists)
def test_list_slice_full_range_is_copy(xs: list[int]) -> None:
    result = c.list_slice(xs, 0, len(xs))
    assert result == xs
    assert result is not xs


@settings(max_examples=200)
@given(_nonempty_int_lists)
def test_deque_fifo_order(xs: list[int]) -> None:
    deque = {'tag': 'deque', 'items': []}
    for item in xs:
        c.deque_push_back(deque, item)
    popped = [c.deque_pop_front(deque) for _ in range(len(xs))]
    assert popped == xs
    assert c.deque_size(deque) == 0


@settings(max_examples=200)
@given(_nonempty_int_lists)
def test_deque_lifo_order(xs: list[int]) -> None:
    deque = {'tag': 'deque', 'items': []}
    for item in xs:
        c.deque_push_back(deque, item)
    popped = [c.deque_pop_back(deque) for _ in range(len(xs))]
    assert popped == list(reversed(xs))


@settings(max_examples=200)
@given(_int_lists)
def test_map_remove_has_sync(xs: list[int]) -> None:
    m = {i: i for i in xs}
    for key in xs:
        c.map_remove(m, key)
        assert not c.map_has(m, key)
    assert c.map_size(m) == 0
