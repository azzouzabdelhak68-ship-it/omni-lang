"""OMNISYS.collections â€” List / Map / Set / Deque / Heap / RingBuffer.

Pure operations on JSON-friendly values. Mirrors ``omnisys/collections.js``:
``omnisys_core.panic`` is used for the shared panic conditions.
"""

from collections.abc import Callable
from typing import Any, TypeAlias

from omnisys_core import panic

Deque: TypeAlias = dict[str, Any]
Heap: TypeAlias = dict[str, Any]
RingBuffer: TypeAlias = dict[str, Any]


def list_push(list_: list[Any], item: Any) -> list[Any]:
    """Append ``item`` to ``list_`` and return the same list."""
    list_.append(item)
    return list_


def list_pop(list_: list[Any]) -> Any:
    """Remove and return the last item; panic when ``list_`` is empty."""
    if len(list_) == 0:
        panic('collections.list_pop on empty list')
    return list_.pop()


def list_get(list_: list[Any], index: int) -> Any:
    """Return the item at ``index``; panic when out of range."""
    if index < 0 or index >= len(list_):
        panic('collections.list_get index out of range')
    return list_[index]


def list_set(list_: list[Any], index: int, value: Any) -> list[Any]:
    """Set ``list_[index]`` to ``value`` and return the list."""
    if index < 0 or index >= len(list_):
        panic('collections.list_set index out of range')
    list_[index] = value
    return list_


def list_slice(list_: list[Any], start: int, end: int) -> list[Any]:
    """Return a new list containing ``list_[start:end]``."""
    return list_[start:end]


def list_append(a: list[Any], b: list[Any]) -> list[Any]:
    """Return a new list with the items of ``a`` followed by those of ``b``."""
    return a + b


def list_contains(list_: list[Any], item: Any) -> bool:
    """Return True when ``item`` is in ``list_``."""
    return item in list_


def list_index_of(list_: list[Any], item: Any) -> int:
    """Return the first index of ``item``, or -1 when absent."""
    if item in list_:
        return list_.index(item)
    return -1


def list_remove(list_: list[Any], index: int) -> list[Any]:
    """Remove the item at ``index`` and return the list; panic when out of range."""
    if index < 0 or index >= len(list_):
        panic('collections.list_remove index out of range')
    del list_[index]
    return list_


def list_sort(list_: list[Any]) -> list[Any]:
    """Return a new list sorted in ascending numeric order."""
    return sorted(list_)


def list_reverse(list_: list[Any]) -> list[Any]:
    """Return a new list with the items in reverse order."""
    return list_[::-1]


def list_fold(list_: list[Any], fn: Callable[[Any, Any], Any], init: Any) -> Any:
    """Reduce ``list_`` left to right as ``fn(acc, item)`` starting from ``init``."""
    acc = init
    for item in list_:
        acc = fn(acc, item)
    return acc


def list_map(list_: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
    """Return a new list with ``fn`` applied to every item."""
    return [fn(item) for item in list_]


def list_filter(list_: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
    """Return a new list with only the items for which ``fn(item)`` is truthy."""
    return [item for item in list_ if fn(item)]


def list_join(list_: list[Any], sep: str) -> str:
    """Return the string forms of the items joined by ``sep``."""
    return sep.join(str(item) for item in list_)


def list_zip(a: list[Any], b: list[Any]) -> list[list[Any]]:
    """Return a new list of ``[x, y]`` pairs up to the shorter length."""
    n = min(len(a), len(b))
    return [[a[i], b[i]] for i in range(n)]


def map_get(map_: dict[Any, Any], key: Any) -> Any:
    """Return ``map_[key]``; raise KeyError when ``key`` is missing."""
    return map_[key]


def map_set(map_: dict[Any, Any], key: Any, value: Any) -> dict[Any, Any]:
    """Set ``map_[key]`` to ``value`` and return the map."""
    map_[key] = value
    return map_


def map_remove(map_: dict[Any, Any], key: Any) -> dict[Any, Any]:
    """Delete ``key`` from ``map_`` when present and return the map."""
    if key in map_:
        del map_[key]
    return map_


def map_has(map_: dict[Any, Any], key: Any) -> bool:
    """Return True when ``key`` is in ``map_``."""
    return key in map_


def map_keys(map_: dict[Any, Any]) -> list[Any]:
    """Return the keys of ``map_`` in insertion order."""
    return list(map_.keys())


def map_values(map_: dict[Any, Any]) -> list[Any]:
    """Return the values of ``map_`` in insertion order."""
    return list(map_.values())


def map_size(map_: dict[Any, Any]) -> int:
    """Return the number of entries in ``map_``."""
    return len(map_)


def set_add(set_: list[Any], item: Any) -> list[Any]:
    """Append ``item`` to the set when absent and return it."""
    if item not in set_:
        set_.append(item)
    return set_


def set_remove(set_: list[Any], item: Any) -> list[Any]:
    """Remove the first occurrence of ``item`` when present and return the set."""
    if item in set_:
        set_.remove(item)
    return set_


def set_has(set_: list[Any], item: Any) -> bool:
    """Return True when ``item`` is in the set."""
    return item in set_


def set_size(set_: list[Any]) -> int:
    """Return the number of unique items in the set."""
    return len(set_)


def set_union(a: list[Any], b: list[Any]) -> list[Any]:
    """Return a new set with the items of ``a`` plus the unique items of ``b``."""
    out = list(a)
    for item in b:
        if item not in out:
            out.append(item)
    return out


def set_intersection(a: list[Any], b: list[Any]) -> list[Any]:
    """Return a new set with only the items present in both ``a`` and ``b``."""
    return [item for item in a if item in b]


def set_difference(a: list[Any], b: list[Any]) -> list[Any]:
    """Return a new set with only the items of ``a`` absent from ``b``."""
    return [item for item in a if item not in b]


def deque_push_front(deque_: Deque, item: Any) -> Deque:
    """Insert ``item`` at the front of ``deque_`` and return it."""
    deque_['items'].insert(0, item)
    return deque_


def deque_push_back(deque_: Deque, item: Any) -> Deque:
    """Append ``item`` to the back of ``deque_`` and return it."""
    deque_['items'].append(item)
    return deque_


def deque_pop_front(deque_: Deque) -> Any:
    """Remove and return the front item; panic when the deque is empty."""
    if len(deque_['items']) == 0:
        panic('collections.deque_pop_front on empty deque')
    return deque_['items'].pop(0)


def deque_pop_back(deque_: Deque) -> Any:
    """Remove and return the back item; panic when the deque is empty."""
    if len(deque_['items']) == 0:
        panic('collections.deque_pop_back on empty deque')
    return deque_['items'].pop()


def deque_size(deque_: Deque) -> int:
    """Return the number of items in ``deque_``."""
    return len(deque_['items'])


def heap_push(heap_: Heap, item: Any) -> Heap:
    """Push ``item`` into the min-heap ``heap_`` and return it."""
    heap_['items'].append(item)
    i = len(heap_['items']) - 1
    while i > 0:
        parent = (i - 1) // 2
        if heap_['items'][parent] <= heap_['items'][i]:
            break
        heap_['items'][parent], heap_['items'][i] = heap_['items'][i], heap_['items'][parent]
        i = parent
    return heap_


def heap_pop(heap_: Heap) -> Any:
    """Remove and return the minimum item; panic when the heap is empty."""
    items = heap_['items']
    if len(items) == 0:
        panic('collections.heap_pop on empty heap')
    top = items[0]
    last = items.pop()
    if len(items) > 0:
        items[0] = last
        i = 0
        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            smallest = i
            if left < len(items) and items[left] < items[smallest]:
                smallest = left
            if right < len(items) and items[right] < items[smallest]:
                smallest = right
            if smallest == i:
                break
            items[smallest], items[i] = items[i], items[smallest]
            i = smallest
    return top


def heap_peek(heap_: Heap) -> Any:
    """Return the minimum item without removing it; panic when the heap is empty."""
    if len(heap_['items']) == 0:
        panic('collections.heap_peek on empty heap')
    return heap_['items'][0]


def heap_size(heap_: Heap) -> int:
    """Return the number of items in ``heap_``."""
    return len(heap_['items'])


def ring_new(capacity: int) -> RingBuffer:
    """Return a new empty ring buffer with the given ``capacity``."""
    return {'tag': 'ring', 'capacity': capacity, 'items': []}


def ring_push(ring_: RingBuffer, item: Any) -> RingBuffer:
    """Append ``item``, evicting from the front when over capacity."""
    ring_['items'].append(item)
    if len(ring_['items']) > ring_['capacity']:
        ring_['items'].pop(0)
    return ring_


def ring_pop(ring_: RingBuffer) -> Any:
    """Remove and return the front item; panic when the ring is empty."""
    if len(ring_['items']) == 0:
        panic('collections.ring_pop on empty ring')
    return ring_['items'].pop(0)


def ring_size(ring_: RingBuffer) -> int:
    """Return the number of items in ``ring_``."""
    return len(ring_['items'])


__all__ = [
    'list_push',
    'list_pop',
    'list_get',
    'list_set',
    'list_slice',
    'list_append',
    'list_contains',
    'list_index_of',
    'list_remove',
    'list_sort',
    'list_reverse',
    'list_fold',
    'list_map',
    'list_filter',
    'list_join',
    'list_zip',
    'map_get',
    'map_set',
    'map_remove',
    'map_has',
    'map_keys',
    'map_values',
    'map_size',
    'set_add',
    'set_remove',
    'set_has',
    'set_size',
    'set_union',
    'set_intersection',
    'set_difference',
    'deque_push_front',
    'deque_push_back',
    'deque_pop_front',
    'deque_pop_back',
    'deque_size',
    'heap_push',
    'heap_pop',
    'heap_peek',
    'heap_size',
    'ring_new',
    'ring_push',
    'ring_pop',
    'ring_size',
]
