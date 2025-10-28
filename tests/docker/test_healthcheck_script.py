"""Regression tests for :mod:`docker.healthcheck`.

The Docker image relies on this probe both for the container level
``HEALTHCHECK`` directive and for local development where engineers may run the
script manually.  The tests exercise the retry loop with deterministic stubs so
future refactors keep the graceful backoff guarantees in place.
"""

from __future__ import annotations

import importlib.util
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Deque, Iterable

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "docker" / "healthcheck.py"
_SPEC = importlib.util.spec_from_file_location("docker_healthcheck", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - defensive guard for CI failures.
    raise RuntimeError(f"unable to load healthcheck module from {_MODULE_PATH}")
healthcheck = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(healthcheck)


class _StubConnection:
    """Mimic :class:`http.client.HTTPConnection` for the health probe tests."""

    def __init__(self, status_code: int) -> None:
        self._status_code = status_code
        self.closed = False

    def request(self, method: str, path: str) -> None:
        # The probe must keep targeting the ``/health`` endpoint with a GET
        # request so the FastAPI application exposes a lightweight status hook.
        assert method == "GET"
        assert path == "/health"

    def getresponse(self) -> SimpleNamespace:
        return SimpleNamespace(status=self._status_code)

    def close(self) -> None:
        self.closed = True


def _stub_factory(sequence: Iterable[object]) -> Callable[[], _StubConnection]:
    """Return a ``_create_connection`` replacement yielding deterministic stubs."""
    queue: Deque[object] = deque(sequence)

    def _factory() -> _StubConnection:
        if not queue:
            raise AssertionError("healthcheck requested more connections than expected")
        value = queue.popleft()
        if isinstance(value, BaseException):
            raise value
        return _StubConnection(int(value))

    return _factory


def _configure_test_retry_window(monkeypatch: pytest.MonkeyPatch, attempts: int) -> None:
    """Shorten the retry window so tests execute instantly."""
    monkeypatch.setattr(healthcheck, "_RETRY_ATTEMPTS", attempts, raising=False)
    monkeypatch.setattr(healthcheck, "_RETRY_DELAY_SECONDS", 0.0, raising=False)
    monkeypatch.setattr(healthcheck.time, "sleep", lambda _seconds: None)


def test_main_succeeds_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 200 status on the first attempt should exit successfully."""
    _configure_test_retry_window(monkeypatch, attempts=1)
    monkeypatch.setattr(healthcheck, "_create_connection", _stub_factory([200]))

    assert healthcheck.main() == 0


def test_main_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transient failures must be retried until a healthy response is observed."""
    _configure_test_retry_window(monkeypatch, attempts=3)
    # Simulate a connection error followed by a 500 response before the probe
    # finally reaches the healthy 200 code on the third attempt.
    sequence = [ConnectionError("dial failure"), 500, 200]
    monkeypatch.setattr(healthcheck, "_create_connection", _stub_factory(sequence))

    assert healthcheck.main() == 0


def test_main_reports_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Once retries are exhausted the script must exit with ``1`` and log context."""
    _configure_test_retry_window(monkeypatch, attempts=2)
    monkeypatch.setattr(
        healthcheck,
        "_create_connection",
        _stub_factory([ConnectionError("dial failure"), TimeoutError("late response")]),
    )

    assert healthcheck.main() == 1
    captured = capsys.readouterr()
    assert "healthcheck failed" in captured.err
