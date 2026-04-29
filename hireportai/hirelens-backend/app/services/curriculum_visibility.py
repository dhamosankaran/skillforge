"""Read-time visibility helpers for Phase 6 curriculum content.

Slice 6.6 §12 D-6 promotes the `_persona_visible_to` /
`_visible_persona_set` / `_allowed_tiers_for_user` trio (plus the
transitive `_resolve_plan` helper) out of the per-service duplicates
introduced by slice 6.5 D-5. Slice 6.5 D-5's rule-of-three escape-hatch
fires explicitly here: `lesson_service`, `quiz_item_study_service`, and
the new `deck_ranker_service` are all consumers.

Migration is **additive** — bodies are byte-identical to the slice 6.5
duplicates, so no behavioural delta. The slice 6.5 inline note re:
deferring extraction is amended in lockstep at this slice's impl
commit.

Specs:
- docs/specs/phase-6/06-read-time-invariants.md §6.3 + §12 D-5 (origin
  of the duplicated helpers).
- docs/specs/phase-6/07-deck-lesson-ranker.md §6.3 + §12 D-6
  (extraction lock).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import inspect

from app.models.user import User


def _persona_visible_to(deck_persona: str, user_persona: Optional[str]) -> bool:
    """True iff a user with ``user_persona`` may see a deck with
    ``persona_visibility == deck_persona``.

    ``'both'`` is visible to every user; the named persona is visible
    only to a user with that persona. Persona-null users see only
    ``'both'``.
    """
    if deck_persona == "both":
        return True
    if user_persona is None:
        return False
    return deck_persona == user_persona


def _visible_persona_set(user: Optional[User]) -> tuple[str, ...]:
    """``Deck.persona_visibility`` values the user is allowed to see.

    Persona-null users see only ``'both'``; persona-set users see
    ``'both'`` + their persona.
    """
    if user is None or user.persona is None:
        return ("both",)
    return ("both", user.persona)


def _resolve_plan(user: Optional[User]) -> Optional[str]:
    """Best-effort plan extraction without triggering a sync lazy-load.

    Returns ``None`` when the subscription relationship is unloaded
    (e.g. service tests that construct a ``User`` directly). Returns
    ``'free'`` when the user has no subscription row or the row is not
    ``status='active'``. Otherwise returns the row's ``plan`` value.
    """
    if user is None:
        return None
    state = inspect(user)
    if "subscription" in state.unloaded:
        return None  # don't trigger lazy load
    sub = user.subscription
    if sub is None:
        return "free"
    if getattr(sub, "status", None) != "active":
        return "free"
    return getattr(sub, "plan", "free")


def _allowed_tiers_for_user(user: Optional[User]) -> tuple[str, ...]:
    """``Deck.tier`` values the user can access given their plan.

    Free users (and persona-null / unloaded-subscription) see only
    ``'foundation'``; paid plans see ``'foundation'`` + ``'premium'``.

    Slice 6.5 §12 D-2 / D-10 lock this server-side guarantee; slice 6.7
    owns the visible UX paywall composition.
    """
    plan = _resolve_plan(user)
    if plan and plan != "free":
        return ("foundation", "premium")
    return ("foundation",)
