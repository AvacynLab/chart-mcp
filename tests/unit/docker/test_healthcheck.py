"""Tests for the Docker healthcheck retry logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Iterable, Iterator, List

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "docker" / "healthcheck.py"
"""Path to the module under test (loaded via ``importlib`` to avoid clashes)."""


def _load_module():
    """Return a fresh instance of the healthcheck module for each test."""
    spec = importlib.util.spec_from_file_location("healthcheck_module", MODULE_PATH)
    assert spec and spec.loader  # narrow the type for mypy
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class DummyConnection:
    """Stand-in HTTP connection that feeds deterministic responses to the probe."""

    def __init__(
        self,
        statuses: Iterable[int] | None = None,
        *,
        request_hook: Callable[[], None] | None = None,
    ) -> None:
        self._statuses: Iterator[int] = iter(statuses or [])
        self._request_hook = request_hook
        self.closed = False
        self.requests: List[str] = []

    def request(self, method: str, path: str) -> None:
        """Record the HTTP call and trigger the optional hook."""
        self.requests.append(f"{method} {path}")
        if self._request_hook:
            self._request_hook()

    def getresponse(self) -> SimpleNamespace:
        """Return a lightweight response object using the configured status."""
        return SimpleNamespace(status=next(self._statuses, 500))

    def close(self) -> None:
        """Mark the connection as closed for assertions."""
        self.closed = True


def test_probe_once_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 200 response should make ``_probe_once`` succeed and close the connection."""
    module = _load_module()
    connection = DummyConnection(statuses=[200])
    monkeypatch.setattr(module, "_create_connection", lambda: connection)

    assert module._probe_once() is True
    assert connection.closed is True


def test_probe_once_failure_handles_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exceptions raised during the request should return ``False`` and still close."""
    module = _load_module()

    def raise_error() -> None:
        raise ConnectionError("temporary network issue")

    connection = DummyConnection(request_hook=raise_error)
    monkeypatch.setattr(module, "_create_connection", lambda: connection)

    assert module._probe_once() is False
    assert connection.closed is True


def test_main_retries_until_probe_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """The main entry point should retry until success and sleep between attempts."""
    module = _load_module()
    outcomes = iter([False, False, True])
    sleeps: List[float] = []

    monkeypatch.setattr(module, "_probe_once", lambda: next(outcomes))
    monkeypatch.setattr(module.time, "sleep", lambda delay: sleeps.append(delay))

    assert module.main() == 0
    assert sleeps == [module._RETRY_DELAY_SECONDS, module._RETRY_DELAY_SECONDS]


def test_main_returns_failure_after_all_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """When all probes fail the exit code should remain non-zero."""
    module = _load_module()
    sleeps: List[float] = []

    monkeypatch.setattr(module, "_probe_once", lambda: False)
    monkeypatch.setattr(module.time, "sleep", lambda delay: sleeps.append(delay))

    assert module.main() == 1
    assert len(sleeps) == module._RETRY_ATTEMPTS - 1
