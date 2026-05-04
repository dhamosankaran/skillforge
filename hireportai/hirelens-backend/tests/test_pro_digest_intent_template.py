"""Privacy ban-list snapshot test for the Pro digest intent block (B-125a).

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §8.5 + §11
AC-X. Defence-in-depth: §6 service ENFORCES the ≥10 cohort threshold;
this test ENFORCES the copy never names individuals, companies, or
peer-comparison framings even when populated.
"""
from __future__ import annotations

from app.schemas.career_intent import AggregateStats, CategoryShare
from app.schemas.pro_digest import DigestPayload
from app.services.pro_digest_service import _build_html


# Per spec §8.5 — copy MUST NOT contain any of these substrings.
_BAN_LIST = (
    "your peers at",
    "users like you",
    "at companies like",
    "based on your background",
    "compared to",
    "top performers",
)


def _digest_with_intent_block() -> DigestPayload:
    return DigestPayload(
        user_id="u-1",
        user_name="Alex",
        user_email="alex@example.com",
        cards_due=0,
        streak=0,
        mission_active=False,
        aggregate_intent_block=AggregateStats(
            target_role="staff",
            target_quarter="2099-Q1",
            cohort_size=42,
            top_categories=[
                CategoryShare(
                    category_name="system design",
                    percent_of_study_time=40.0,
                ),
                CategoryShare(
                    category_name="distributed systems",
                    percent_of_study_time=28.0,
                ),
                CategoryShare(
                    category_name="agentic AI",
                    percent_of_study_time=18.0,
                ),
            ],
        ),
    )


def test_intent_block_renders_aggregate_copy():
    """Sanity — when aggregate block is present, the section is visible
    and contains the percent + category text."""
    html = _build_html(_digest_with_intent_block())
    # Section is visible (no display:none on the wrapper).
    assert 'data-section="intent"' in html
    # The wrapper for the visible block does NOT carry display:none in its
    # style attribute. Other sections (cards/mission/scan) may, since the
    # payload supplies no engagement signal there.
    intent_idx = html.index('data-section="intent"')
    intent_open_close = html.find(">", intent_idx)
    intent_open_tag = html[intent_idx:intent_open_close]
    assert "display:none" not in intent_open_tag
    # Copy contains aggregate framing for the role.
    assert "Staff" in html
    assert "system design" in html
    assert "40" in html  # percent rendered


def test_intent_block_template_omits_section_when_no_block():
    payload = DigestPayload(
        user_id="u-1",
        user_name="Alex",
        user_email="alex@example.com",
        cards_due=3,
        streak=2,
        mission_active=False,
    )
    html = _build_html(payload)
    intent_idx = html.index('data-section="intent"')
    intent_open_close = html.find(">", intent_idx)
    intent_open_tag = html[intent_idx:intent_open_close]
    assert "display:none" in intent_open_tag


def test_intent_block_does_not_contain_forbidden_phrases():
    """AC-X — privacy ban list. The rendered HTML must NOT contain any of
    the §8.5 forbidden substrings."""
    html = _build_html(_digest_with_intent_block()).lower()
    for phrase in _BAN_LIST:
        assert phrase.lower() not in html, (
            f"Intent block copy must not contain banned phrase: {phrase!r}"
        )
