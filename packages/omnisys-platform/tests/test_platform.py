"""Unit tests for OMNISYS.platform."""

from __future__ import annotations

import sys
import time

import omnisys_platform as platform
import pytest
from omnisys_core import PanicError


def test_os_returns_non_empty_string() -> None:
    value = platform.os()
    assert isinstance(value, str)
    assert value


def test_arch_returns_non_empty_string() -> None:
    value = platform.arch()
    assert isinstance(value, str)
    assert value


def test_now_is_non_negative_float() -> None:
    value = platform.now()
    assert isinstance(value, float)
    assert value >= 0


def test_now_increases_across_calls() -> None:
    first = platform.now()
    second = platform.now()
    assert second >= first


def test_info_keys() -> None:
    assert set(platform.info()) == {'os', 'arch', 'python', 'runtime'}


def test_info_values_are_strings() -> None:
    for value in platform.info().values():
        assert isinstance(value, str)


def test_info_runtime_is_python() -> None:
    assert platform.info()['runtime'] == 'python'


def test_info_reports_python_version() -> None:
    assert platform.info()['python'] == sys.version.split()[0]


def test_info_os_and_arch_match_accessors() -> None:
    info = platform.info()
    assert info['os'] == platform.os()
    assert info['arch'] == platform.arch()


def test_env_returns_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OMNISYS_PLATFORM_TEST_KEY', 'hello')
    assert platform.env('OMNISYS_PLATFORM_TEST_KEY') == 'hello'


def test_env_fallback_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('OMNISYS_PLATFORM_TEST_MISSING', raising=False)
    assert platform.env('OMNISYS_PLATFORM_TEST_MISSING') == ""
    assert platform.env('OMNISYS_PLATFORM_TEST_MISSING', "fallback") == "fallback"


def test_sleep_ms_returns_argument() -> None:
    assert platform.sleep_ms(7) == 7


def test_sleep_ms_zero_returns_immediately() -> None:
    started = time.perf_counter()
    platform.sleep_ms(0)
    assert time.perf_counter() - started < 1.0


def test_sleep_ms_elapsed_is_non_negative() -> None:
    started = time.perf_counter()
    platform.sleep_ms(20)
    assert time.perf_counter() - started >= 0.0


def test_capabilities_contains_none_and_process() -> None:
    caps = platform.capabilities()
    assert 'none' in caps
    assert 'process' in caps


def test_capabilities_is_python_lane_set() -> None:
    assert platform.capabilities() == [
        'none',
        'process',
        'filesystem',
        'camera',
        'microphone',
        'graphics',
    ]
