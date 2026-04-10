# Spec 13 — Skill Radar + Activity Heatmap

**Phase:** 2 | **Status:** in-progress | **Priority:** P1

## Goal
Give users a visual dashboard showing (a) how well they've covered each
flashcard category (radar/spider chart) and (b) a GitHub-style activity
heatmap of daily review sessions over the last 90 days.

## Data Model
No new tables. Reads from existing `categories`, `cards`, `card_progress`.

## Backend

### Service: `app/services/progress_service.py`

| Method | Signature | Returns |
|--------|-----------|---------|
| `get_category_coverage` | `(user_id, db) -> list[CategoryCoverage]` | `{ category, total_cards, studied, mastery_pct }` per category |
| `get_activity_heatmap` | `(user_id, days, db) -> list[HeatmapDay]` | `{ date, review_count }[]` for the last *days* days |

**`mastery_pct`** = cards in `review` state / total cards in that category
(review = successfully graduated from learning).

**`review_count`** = distinct card_progress rows where `last_reviewed` falls
on a given UTC date for the user.

### API Routes

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/v1/progress/radar` | `RadarResponse { categories: CategoryCoverage[] }` |
| `GET` | `/api/v1/progress/heatmap?days=90` | `HeatmapResponse { days: HeatmapDay[] }` |

Both require `Depends(get_current_user)`.

## Frontend

### `SkillRadar.tsx`
- recharts `RadarChart` with `PolarGrid`, `PolarAngleAxis`, `Radar` fill.
- Fetches `/api/v1/progress/radar` on mount.
- Each axis = one category, value = `mastery_pct` (0-100).

### `ActivityHeatmap.tsx`
- CSS grid, 7 rows (Mon-Sun) x N weeks.
- Fetches `/api/v1/progress/heatmap?days=90` on mount.
- Cell color intensity = review_count (0=empty, 1-2=light, 3-4=medium, 5+=dark).
- Tooltip on hover shows date + count.

Both components are added to the **Profile** page below the existing
study history section.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `/api/v1/progress/radar` returns all seeded categories with correct `mastery_pct` |
| AC-2 | `/api/v1/progress/heatmap` returns exactly `days` entries, most recent first |
| AC-3 | Radar chart renders with at least 3 axes when categories exist |
| AC-4 | Heatmap shows today's cell highlighted after a review |
| AC-5 | Both endpoints respond within 200ms for a user with 500 card_progress rows |

## Tests

| Test | Validates |
|------|-----------|
| `test_radar_returns_all_categories` | AC-1 |
| `test_heatmap_shows_activity_days` | AC-2 |
