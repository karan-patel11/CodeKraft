"""
Metrics Tracker — captures per-request latency breakdowns and
aggregates for monitoring system health.

All metrics are held in-memory (resets on cold start). For production,
plug into Vercel Analytics, Datadog, or Prometheus.
"""

import time
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import deque
from typing import Optional


@dataclass
class RequestMetrics:
    """Latency breakdown for a single /api/analyze request."""
    total_ms: float = 0.0
    static_analysis_ms: float = 0.0
    classifier_ms: float = 0.0
    rule_engine_ms: float = 0.0
    llm_enrichment_ms: float = 0.0
    classification_source: str = ""     # "codebert" | "static_fallback"
    classification_confidence: float = 0.0
    error_category: str = ""
    findings_count: int = 0
    code_lines: int = 0
    complexity: float = 0.0

    def to_dict(self):
        return {
            "latency": {
                "total_ms": round(self.total_ms, 2),
                "static_analysis_ms": round(self.static_analysis_ms, 2),
                "classifier_ms": round(self.classifier_ms, 2),
                "rule_engine_ms": round(self.rule_engine_ms, 2),
                "llm_enrichment_ms": round(self.llm_enrichment_ms, 2),
                "instant_response_ms": round(
                    self.static_analysis_ms + self.classifier_ms + self.rule_engine_ms, 2
                ),
            },
            "classification": {
                "source": self.classification_source,
                "confidence": round(self.classification_confidence, 4),
                "category": self.error_category,
            },
            "code_stats": {
                "lines": self.code_lines,
                "findings": self.findings_count,
                "complexity": round(self.complexity, 2),
            },
        }


class MetricsAggregator:
    """
    In-memory rolling metrics aggregator.
    Keeps the last N requests for computing averages.
    """

    def __init__(self, window_size: int = 100):
        self._window: deque[RequestMetrics] = deque(maxlen=window_size)
        self.total_requests: int = 0
        self.total_errors: int = 0

    def record(self, m: RequestMetrics):
        self._window.append(m)
        self.total_requests += 1

    def record_error(self):
        self.total_errors += 1

    def summary(self) -> dict:
        if not self._window:
            return {"total_requests": 0, "message": "No requests recorded yet."}

        n = len(self._window)
        avg_total = sum(m.total_ms for m in self._window) / n
        avg_instant = sum(
            m.static_analysis_ms + m.classifier_ms + m.rule_engine_ms
            for m in self._window
        ) / n
        avg_llm = sum(m.llm_enrichment_ms for m in self._window) / n
        avg_confidence = sum(m.classification_confidence for m in self._window) / n

        # Source breakdown
        sources = {}
        for m in self._window:
            sources[m.classification_source] = sources.get(m.classification_source, 0) + 1

        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "window_size": n,
            "avg_total_ms": round(avg_total, 2),
            "avg_instant_response_ms": round(avg_instant, 2),
            "avg_llm_enrichment_ms": round(avg_llm, 2),
            "avg_confidence": round(avg_confidence, 4),
            "classification_sources": sources,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_aggregator = MetricsAggregator()


def get_aggregator() -> MetricsAggregator:
    return _aggregator


@contextmanager
def measure(label: str = ""):
    """Context manager to measure elapsed time in milliseconds."""
    start = time.perf_counter()
    result = {"elapsed_ms": 0.0}
    try:
        yield result
    finally:
        result["elapsed_ms"] = (time.perf_counter() - start) * 1000
