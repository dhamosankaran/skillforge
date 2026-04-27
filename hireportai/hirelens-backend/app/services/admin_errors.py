"""Service-layer error classes shared across admin authoring services.

Spec: docs/specs/phase-6/04-admin-authoring.md §4.1.4 + §12 D-11.

Mirrors slice 6.2's `quiz_item_study_service` error pattern. Errors live
in this single shared module because the three admin services (decks,
lessons, quiz_items) all raise the same handful of conflict / not-found
shapes; route handlers translate them into HTTP status codes (404 / 409).

`SUBSTANTIVE_EDIT_THRESHOLD = 0.15` is the BE-side anchor for the §7.2
character-delta classification rule (D-17). FE mirrors the constant in
`src/utils/lessonEdit.ts` (slice 6.4b-2). Drift between the two is
caught server-side via `EditClassificationConflictError` per §7.1.
"""
from __future__ import annotations

# >15% char-delta on concept_md / production_md / examples_md → substantive.
# Cross-ref: spec §7.2, FE-side mirror in src/utils/lessonEdit.ts (slice 6.4b-2).
SUBSTANTIVE_EDIT_THRESHOLD: float = 0.15


class DeckSlugConflictError(Exception):
    """Slug already taken on `decks` (UNIQUE constraint). 409."""


class DeckNotFoundError(Exception):
    """Unknown deck_id. 404."""


class LessonSlugConflictError(Exception):
    """Composite UNIQUE (deck_id, slug) collision on `lessons`. 409."""


class LessonNotFoundError(Exception):
    """Unknown lesson_id. 404."""


class LessonArchivedError(Exception):
    """Caller is mutating an archived lesson (e.g. publish, create child quiz). 409."""


class QuizItemNotFoundError(Exception):
    """Unknown quiz_item_id. 404.

    NB: a same-named error in `app.services.quiz_item_study_service` covers
    the user-facing FSRS path; the duplicate is locked-in by slice 6.2 D-1
    until slice 6.15 cleanup. They serve different code paths.
    """


class EditClassificationConflictError(Exception):
    """Admin's `edit_classification` claim contradicts the §7 rule. 409.

    The route layer surfaces the conflict so FE can re-prompt the modal
    with the corrected classification + cascade preview.
    """

    def __init__(self, expected: str, claimed: str, fields: list[str]) -> None:
        self.expected = expected
        self.claimed = claimed
        self.fields = fields
        super().__init__(
            f"edit_classification mismatch: claimed={claimed!r} "
            f"expected={expected!r} (fields exceeding threshold: {fields})"
        )
