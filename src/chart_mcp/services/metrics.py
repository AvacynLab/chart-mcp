"""Prometheus metrics helpers used across the Market Charting Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from prometheus_client import (  # type: ignore[import-not-found]
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)


@dataclass
class MetricsRegistry:
    """Container owning all Prometheus collectors exposed by the API.

    The registry keeps track of three high-level signals mandated by the backlog:

    * ``provider_errors_total`` counts upstream provider failures per exchange so
      operators can watch for degraded data sources.
    * ``stream_stage_duration_seconds`` records the latency of each SSE pipeline
      stage. These timings help validate the SLA for real-time analysis.
    * ``stream_events_total`` captures the number of SSE packets produced by
      event type (``step:start``, ``token``, ``heartbeat``...).

    The class centralises the collectors to make resetting state in tests simple
    and to provide a consistent ``CollectorRegistry`` for the ``/metrics`` route.
    """

    registry: CollectorRegistry = field(init=False)
    provider_errors: Counter = field(init=False)
    stage_latency: Histogram = field(init=False)
    events_emitted: Counter = field(init=False)

    def __post_init__(self) -> None:
        self._initialise()

    def _initialise(self) -> None:
        """Instantiate collectors on a fresh registry."""
        # A private registry keeps unit tests isolated: resetting re-creates the
        # collectors without touching the global default registry shared by other
        # libraries or applications that may be imported in the same process.
        self.registry = CollectorRegistry()
        self.provider_errors = Counter(
            "provider_errors_total",
            "Number of upstream provider errors grouped by provider, exchange and reason.",
            ("provider", "exchange", "reason"),
            registry=self.registry,
        )
        self.stage_latency = Histogram(
            "stream_stage_duration_seconds",
            "Observed duration of each streaming pipeline stage in seconds.",
            ("stage",),
            registry=self.registry,
            # Explicit buckets provide visibility into sub-second latencies while
            # still covering longer-running stages such as LLM summarisation.
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
        )
        self.events_emitted = Counter(
            "stream_events_total",
            "Total number of SSE packets emitted grouped by event name.",
            ("event",),
            registry=self.registry,
        )

    def reset(self) -> None:
        """Reset all collectors to an empty state (useful for deterministic tests)."""
        self._initialise()

    def record_provider_error(self, provider: str, exchange: str, reason: str) -> None:
        """Increment the provider error counter for the supplied context."""
        cleaned_reason = reason or "unknown"
        self.provider_errors.labels(provider=provider, exchange=exchange, reason=cleaned_reason).inc()

    def observe_stage_duration(self, stage: str, seconds: float) -> None:
        """Record how long a pipeline stage took in seconds (clamped to >= 0)."""
        duration = max(0.0, float(seconds))
        self.stage_latency.labels(stage=stage).observe(duration)

    def increment_stream_event(self, event: str) -> None:
        """Increment the SSE event counter for ``event``."""
        self.events_emitted.labels(event=event).inc()

    def render(self) -> bytes:
        """Return the latest metrics snapshot in Prometheus exposition format."""
        return generate_latest(self.registry)

    @property
    def content_type(self) -> str:
        """Expose the canonical content type for the Prometheus text format."""
        return CONTENT_TYPE_LATEST


# Singleton used across the application. Tests may call ``metrics.reset()`` to
# ensure a blank slate prior to exercising behaviours.
metrics: Final[MetricsRegistry] = MetricsRegistry()


__all__ = ["metrics", "MetricsRegistry"]
