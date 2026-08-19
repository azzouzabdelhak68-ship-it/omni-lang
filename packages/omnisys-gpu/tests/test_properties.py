"""Property-based tests for OMNISYS.gpu."""

import math

import omnisys_gpu as gpu
import pytest
from hypothesis import given
from hypothesis import strategies as st

_NUM = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
_VEC = st.lists(_NUM, min_size=1, max_size=20)


@st.composite
def _two_matrices(draw):
    m = draw(st.integers(min_value=1, max_value=4))
    k = draw(st.integers(min_value=1, max_value=4))
    n = draw(st.integers(min_value=1, max_value=4))
    a = draw(st.lists(st.lists(_NUM, min_size=k, max_size=k), min_size=m, max_size=m))
    b = draw(st.lists(st.lists(_NUM, min_size=n, max_size=n), min_size=k, max_size=k))
    return a, b


@given(st.lists(_NUM, min_size=0, max_size=20))
def test_buffer_copies_contents(v: list[float]) -> None:
    buf = gpu.buffer(v)
    assert buf['tag'] == 'gpu.buffer'
    assert buf['data'] == v


@given(st.integers(min_value=-5, max_value=10))
def test_compute_runs_exactly_n_times(size: int) -> None:
    count = 0

    def kernel(i: int, _data: object) -> int:
        nonlocal count
        count += 1
        return i

    out = gpu.compute(kernel, [], size)
    assert out == list(range(max(0, int(size))))
    assert count == max(0, int(size))


@given(st.lists(st.integers(min_value=0, max_value=100), max_size=20))
def test_parallel_preserves_order_and_indices(v: list[int]) -> None:
    out = gpu.parallel(lambda i, item: (i, item), v)
    assert out == list(enumerate(v))


@given(_VEC, _VEC)
def test_add_matches_element_wise(a: list[float], b: list[float]) -> None:
    n = min(len(a), len(b))
    assert gpu.add(a[:n], b[:n]) == [a[i] + b[i] for i in range(n)]


@given(_VEC, st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False))
def test_scale_matches_element_wise(a: list[float], factor: float) -> None:
    assert gpu.scale(a, factor) == [v * factor for v in a]


@given(_VEC, _VEC)
def test_dot_matches_pairwise_sum(a: list[float], b: list[float]) -> None:
    n = min(len(a), len(b))
    assert gpu.dot(a[:n], b[:n]) == sum(x * y for x, y in zip(a[:n], b[:n], strict=True))


@given(st.lists(_NUM, min_size=1, max_size=20).filter(lambda xs: any(abs(x) >= 1e-3 for x in xs)))
def test_normalize_yields_unit_length(v: list[float]) -> None:
    result = gpu.normalize(v)
    assert math.hypot(*result) == pytest.approx(1.0)


@given(_two_matrices())
def test_matmul_matches_triple_loop(ab) -> None:
    a, b = ab
    out = gpu.matmul(a, b)
    assert len(out) == len(a)
    assert len(out[0]) == len(b[0])
    for i in range(len(a)):
        for j in range(len(b[0])):
            assert out[i][j] == sum(a[i][p] * b[p][j] for p in range(len(b)))
