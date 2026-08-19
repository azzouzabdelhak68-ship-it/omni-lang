"""Unit tests for OMNISYS.gpu."""

from typing import Any

import omnisys_core as core
import omnisys_gpu as gpu
import pytest


def test_buffer_copies_input() -> None:
    data = [1, 2, 3]
    buf = gpu.buffer(data)
    data.append(4)
    assert buf == {'tag': 'gpu.buffer', 'data': [1, 2, 3]}


def test_buffer_empty_data() -> None:
    assert gpu.buffer([]) == {'tag': 'gpu.buffer', 'data': []}


def test_compute_calls_kernel_with_index_and_input() -> None:
    calls: list[tuple[int, object]] = []

    def kernel(i: int, data: object) -> int:
        calls.append((i, data))
        return i

    out = gpu.compute(kernel, [1, 2], 3)
    assert out == [0, 1, 2]
    assert calls == [(0, [1, 2]), (1, [1, 2]), (2, [1, 2])]


def test_compute_clamps_negative_and_zero_size() -> None:
    def kernel(i: int, _data: object) -> int:
        return i

    assert gpu.compute(kernel, [], -3) == []
    assert gpu.compute(kernel, [], 0) == []
    assert gpu.compute(kernel, [], 2.7) == [0, 1]


def test_parallel_enumerates_in_order() -> None:
    out = gpu.parallel(lambda i, item: f'{i}:{item}', ['a', 'b', 'c'])
    assert out == ['0:a', '1:b', '2:c']


def test_parallel_empty_or_none_input() -> None:
    def kernel(i: int, item: Any) -> Any:
        return (i, item)

    assert gpu.parallel(kernel, []) == []
    assert gpu.parallel(kernel, None) == []


def test_add_element_wise() -> None:
    assert gpu.add([1, 2, 3], [4, 5, 6]) == [5, 7, 9]


def test_add_length_mismatch_panics() -> None:
    with pytest.raises(core.PanicError, match='gpu.add: length mismatch'):
        gpu.add([1], [1, 2])


def test_scale() -> None:
    assert gpu.scale([1, 2, 3], 0.5) == [0.5, 1.0, 1.5]


def test_dot() -> None:
    assert gpu.dot([1, 2, 3], [4, 5, 6]) == 32


def test_dot_length_mismatch_panics() -> None:
    with pytest.raises(core.PanicError, match='gpu.dot: length mismatch'):
        gpu.dot([1], [1, 2])


def test_matmul() -> None:
    assert gpu.matmul([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]


def test_matmul_rectangular() -> None:
    a = [[1, 2, 3], [4, 5, 6]]
    b = [[7, 8], [9, 10], [11, 12]]
    assert gpu.matmul(a, b) == [[58, 64], [139, 154]]


def test_matmul_shape_mismatch_panics() -> None:
    with pytest.raises(core.PanicError, match='gpu.matmul: incompatible matrices'):
        gpu.matmul([[1, 2, 3]], [[1, 2], [3, 4]])


def test_normalize_non_zero_vector() -> None:
    result = gpu.normalize([3.0, 4.0])
    assert result[0] == pytest.approx(0.6)
    assert result[1] == pytest.approx(0.8)


def test_normalize_zero_vector_returns_copy() -> None:
    a = [0.0, 0.0, 0.0]
    result = gpu.normalize(a)
    assert result == a
    result.append(1.0)
    assert a == [0.0, 0.0, 0.0]


def test_device_info_shape() -> None:
    info = gpu.device_info()
    assert info == {
        'tag': 'gpu.device',
        'name': 'portable-cpu',
        'lanes': ['js-fallback'],
        'cores': 1,
    }
