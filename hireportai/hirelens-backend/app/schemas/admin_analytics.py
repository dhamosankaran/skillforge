"""Admin analytics response schemas (spec #38 §API Contract, E-018b slice 2/4).

Slice 2 ships AC-2 (metrics) and AC-3 (performance) — the latter with two
fields (`api_latency`, `error_rate_24h_pct`) deferred to Slice 3 / a follow-up
because no backend latency/error source exists yet and PostHog Query API is
forbidden by §Rollout Slice 2. Deferred fields are expressed as
`Optional[...]` paired with an `available: bool` marker so the UI can render
a "Coming soon" tile without coding around nulls ambiguously. Follow-ups
tracked as E-018b-follow (latency) and E-018b-follow-errors (error rate).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """Single OKR tile with 7d + 30d deltas (spec §API Contract §1).

    `delta_7d_pct` / `delta_30d_pct` are 0.0 (not `inf`) when the historical
    value is 0 — see `test_metrics_divide_by_zero` in the spec §Test Plan.
    """

    current: float
    d7_ago: float
    d30_ago: float
    delta_7d_pct: float
    delta_30d_pct: float


class MetricsResponse(BaseModel):
    """Six PRD §1.4 OKRs (spec AC-2)."""

    registered_users: MetricValue
    paying_pro_users: MetricValue
    dau_mau_ratio: MetricValue          # 0.0–1.0
    avg_streak_length: MetricValue      # days
    ats_to_pro_conversion: MetricValue  # 0.0–1.0
    monthly_churn: MetricValue          # 0.0–1.0
    generated_at: datetime
    from_cache: bool


class RouteLatency(BaseModel):
    """Top-N route latency row (spec §API Contract §2).

    Deferred in Slice 2: `api_latency` is emitted as an empty list with the
    response-level `api_latency_available: false` marker. Rendering the type
    anyway so the schema stays spec-verbatim for consumers that will light up
    the tile in Slice 3 / E-018b-follow.
    """

    route: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    request_count: int


class PerformanceResponse(BaseModel):
    """Operational snapshot (spec AC-3).

    Deferred fields (Slice 3 / follow-up BACKLOG):
    - `api_latency`: empty list + `api_latency_available: false`. No backend
      latency source today; PostHog Query API forbidden by Slice 2 rollout.
    - `error_rate_24h_pct`: None + `error_rate_available: false`. Same reason.

    Live fields this slice:
    - `llm_spend_estimate_usd`: sum(`usage_logs.tokens_consumed`) × tier
      price in `llm_router.TIER_PRICE_USD_PER_1M_TOKENS`. Today's number is
      a lower bound because most call-sites pass `tokens=0` through
      `check_and_increment`; only `/api/v1/resume/optimize` passes real
      token counts. When per-site instrumentation lands the estimate will
      tighten automatically.
    - `llm_spend_breakdown`: keyed by `feature_used` (not model — same
      instrumentation gap). Spec text says "per-model"; we pick the
      narrower source that exists today and leave a schema note.
    - `stripe_webhook_success_24h_pct`: today `stripe_events` only stores
      successful processings, so the ratio is always 100% when any row
      exists. Marked honestly: returns `None` + `stripe_webhook_available:
      false` when no rows in window, `100.0` with the marker true
      otherwise. Proper success-vs-failure tracking needs a failure
      counter — tracked under E-018b-follow-errors.
    """

    llm_spend_estimate_usd: float
    llm_spend_breakdown: dict[str, float] = Field(default_factory=dict)
    api_latency: list[RouteLatency] = Field(default_factory=list)
    api_latency_available: bool
    error_rate_24h_pct: Optional[float]
    error_rate_available: bool
    stripe_webhook_success_24h_pct: Optional[float]
    stripe_webhook_available: bool
    generated_at: datetime
    from_cache: bool
