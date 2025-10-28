"""Lightweight Prometheus client shim used for tests and local development.

This module provides a tiny subset of the real ``prometheus_client`` package so
that the application can expose metrics without pulling the full dependency at
runtime.  The implementation intentionally mirrors the API surface we exercise
in the project (``CollectorRegistry``, ``Counter``, ``Histogram`` and
``generate_latest``) while keeping the internal model simple enough for unit
tests.

The goal is to make metrics-focused tests deterministic and fast: we only store
values in memory and render a textual exposition format that matches what the
official client library would emit for the features we rely on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


class CollectorRegistry:
    """In-memory registry storing collectors registered by the application."""

    def __init__(self) -> None:
        self._collectors: List[BaseCollector] = []

    def register(self, collector: "BaseCollector") -> None:
        """Store ``collector`` so ``generate_latest`` can access it later."""
        if collector not in self._collectors:
            self._collectors.append(collector)

    def collect(self) -> Iterable["BaseCollector"]:
        """Return a snapshot of the registered collectors."""
        return list(self._collectors)


@dataclass
class Sample:
    """Single Prometheus sample captured for exposition."""

    name: str
    labels: Tuple[Tuple[str, str], ...]
    value: float

    def format(self) -> str:
        label_str = "".join([f'{key}="{value}"' for key, value in self.labels])
        if label_str:
            label_str = "{" + ",".join(f'{k}="{v}"' for k, v in self.labels) + "}"
        return f"{self.name}{label_str} {self.value}"


class BaseCollector:
    """Common interface for concrete collectors."""

    def __init__(self, name: str, documentation: str, registry: CollectorRegistry) -> None:
        self.name = name
        self.documentation = documentation
        self.registry = registry
        registry.register(self)

    def collect(self) -> Iterable[Sample]:
        raise NotImplementedError


class _Child:
    """Helper exposing ``inc`` / ``observe`` operations for label sets."""

    def __init__(self, collector: "Counter", labels: Tuple[str, ...]) -> None:
        self.collector = collector
        self.labels = labels

    def inc(self, amount: float = 1.0) -> None:
        self.collector._increment(self.labels, float(amount))


class _HistogramChild:
    """Histogram-specific helper handling observations for label sets."""

    def __init__(self, collector: "Histogram", labels: Tuple[str, ...]) -> None:
        self.collector = collector
        self.labels = labels

    def observe(self, value: float) -> None:
        self.collector._observe(self.labels, float(value))


class Counter(BaseCollector):
    """Minimal counter implementation tracking labelled increments."""

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Tuple[str, ...] | Tuple[str, ...] = (),
        *,
        registry: CollectorRegistry,
    ) -> None:
        super().__init__(name, documentation, registry)
        self.labelnames = tuple(labelnames)
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, *args: str, **kwargs: str) -> _Child:
        """Return a helper scoped to the provided label values."""
        if args and kwargs:
            raise ValueError("Provide either positional or keyword labels, not both")
        if kwargs:
            labels = tuple(kwargs[name] for name in self.labelnames)
        else:
            if len(args) != len(self.labelnames):
                raise ValueError("Incorrect number of label values")
            labels = tuple(args)
        return _Child(self, labels)

    def _increment(self, labels: Tuple[str, ...], amount: float) -> None:
        self._values[labels] = self._values.get(labels, 0.0) + amount

    def collect(self) -> Iterable[Sample]:
        """Yield Prometheus samples for each populated label set."""
        for labels, value in self._values.items():
            label_pairs = tuple(zip(self.labelnames, labels, strict=True))
            yield Sample(self.name, label_pairs, value)


@dataclass
class HistogramState:
    """Mutable histogram state for a specific label set."""

    buckets: List[float]
    bucket_counts: List[float] = field(default_factory=list)
    count: float = 0.0
    sum: float = 0.0

    def __post_init__(self) -> None:
        self.bucket_counts = [0.0 for _ in self.buckets]


class Histogram(BaseCollector):
    """Simplified histogram with explicit bucket boundaries."""

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Tuple[str, ...] | Tuple[str, ...] = (),
        *,
        registry: CollectorRegistry,
        buckets: Tuple[float, ...] = (0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
    ) -> None:
        super().__init__(name, documentation, registry)
        self.labelnames = tuple(labelnames)
        self.buckets = list(buckets)
        self._states: Dict[Tuple[str, ...], HistogramState] = {}

    def labels(self, *args: str, **kwargs: str) -> _HistogramChild:
        """Return a helper scoped to a histogram label set."""
        if kwargs:
            labels = tuple(kwargs[name] for name in self.labelnames)
        else:
            if len(args) != len(self.labelnames):
                raise ValueError("Incorrect number of label values")
            labels = tuple(args)
        if labels not in self._states:
            self._states[labels] = HistogramState(self.buckets.copy())
        return _HistogramChild(self, labels)

    def _observe(self, labels: Tuple[str, ...], value: float) -> None:
        state = self._states.setdefault(labels, HistogramState(self.buckets.copy()))
        state.count += 1.0
        state.sum += value
        for idx, boundary in enumerate(state.buckets):
            if value <= boundary:
                state.bucket_counts[idx] += 1.0
        # Ensure the +Inf bucket always accumulates.
        if state.buckets and state.buckets[-1] != float("inf"):
            state.bucket_counts[-1] += 1.0

    def collect(self) -> Iterable[Sample]:
        """Yield histogram bucket, sum and count samples."""
        for labels, state in self._states.items():
            label_pairs = tuple(zip(self.labelnames, labels, strict=True))
            cumulative = 0.0
            for count, boundary in zip(state.bucket_counts, state.buckets, strict=True):
                cumulative = count
                le_labels = label_pairs + (("le", f"{boundary}"),)
                yield Sample(f"{self.name}_bucket", le_labels, cumulative)
            inf_labels = label_pairs + (("le", "+Inf"),)
            yield Sample(f"{self.name}_bucket", inf_labels, state.count)
            yield Sample(f"{self.name}_count", label_pairs, state.count)
            yield Sample(f"{self.name}_sum", label_pairs, state.sum)


def generate_latest(registry: CollectorRegistry) -> bytes:
    """Render the registry contents using the Prometheus text exposition format."""
    lines: List[str] = []
    for collector in registry.collect():
        lines.append(f"# HELP {collector.name} {collector.documentation}")
        metric_type = "histogram" if isinstance(collector, Histogram) else "counter"
        lines.append(f"# TYPE {collector.name} {metric_type}")
        for sample in collector.collect():
            lines.append(sample.format())
    lines.append("")
    return "\n".join(lines).encode()


__all__ = [
    "CollectorRegistry",
    "Counter",
    "Histogram",
    "generate_latest",
    "CONTENT_TYPE_LATEST",
]
