"""Tests for the Pro digest HTML template substitution (Phase 6 slice 6.14).

Spec: docs/specs/phase-6/14-daily-digest-cron.md §10.3 + §11 AC-14 + §12 D-4.

Pure Python-side substitution (no Jinja2 — mirrors Phase-2
``reminder_service.build_email_body`` ``str.replace`` pattern).
"""
from __future__ import annotations

import pytest

from app.schemas.pro_digest import DigestPayload
from app.services import pro_digest_service


def _payload(**overrides) -> DigestPayload:
    base = dict(
        user_id="u-1",
        user_name="Pro User",
        user_email="pro@example.com",
        cards_due=5,
        streak=3,
        mission_active=True,
        mission_days_left=10,
        last_scan_score=82,
        last_scan_delta=4,
    )
    base.update(overrides)
    return DigestPayload(**base)


def test_template_populates_all_fields_when_full_payload():
    """AC-14 — render full payload (mission + scan + cards), no broken HTML."""
    html = pro_digest_service._build_html(_payload())

    assert "Pro User" in html
    assert "5</strong> cards due" in html
    assert "3</strong> days" in html
    assert "10</strong> days until target" in html
    assert "82</strong>" in html
    assert "+4 vs prior" in html
    # No unsubstituted braces.
    assert "{{" not in html


def test_template_hides_cards_section_when_zero_cards_due():
    """AC-14 — empty-section variant via display:none on data-section=cards."""
    html = pro_digest_service._build_html(
        _payload(cards_due=0, mission_active=True)
    )
    # The cards-section div carries the inline display:none style.
    assert 'data-section="cards" style="display:none;' in html
    # Mission still rendered.
    assert 'data-section="mission" style="padding:16px' in html


def test_template_hides_mission_and_scan_when_only_cards_due():
    """AC-14 — only cards section visible when no mission and no scan."""
    html = pro_digest_service._build_html(
        _payload(
            cards_due=2,
            streak=0,
            mission_active=False,
            mission_days_left=None,
            last_scan_score=None,
            last_scan_delta=None,
        )
    )
    assert 'data-section="cards" style="padding:16px' in html
    assert 'data-section="mission" style="display:none;' in html
    assert 'data-section="scan" style="display:none;' in html
    # Streak unit grammar: 0 days, not "0 day".
    assert "0</strong> days" in html


def test_template_no_unrendered_braces_for_streak_unit():
    """Singular vs plural streak unit branch."""
    html_one = pro_digest_service._build_html(_payload(streak=1))
    html_many = pro_digest_service._build_html(_payload(streak=5))
    assert "1</strong> day" in html_one
    assert "5</strong> days" in html_many


def test_template_scan_delta_negative_and_zero_branches():
    """Delta-display branches: positive / negative / zero / no prior scan."""
    html_pos = pro_digest_service._build_html(
        _payload(last_scan_score=85, last_scan_delta=4)
    )
    html_neg = pro_digest_service._build_html(
        _payload(last_scan_score=70, last_scan_delta=-3)
    )
    html_zero = pro_digest_service._build_html(
        _payload(last_scan_score=80, last_scan_delta=0)
    )
    html_first = pro_digest_service._build_html(
        _payload(last_scan_score=75, last_scan_delta=None)
    )
    assert "+4 vs prior" in html_pos
    assert "-3 vs prior" in html_neg
    assert "unchanged" in html_zero
    assert "no prior scan" in html_first
