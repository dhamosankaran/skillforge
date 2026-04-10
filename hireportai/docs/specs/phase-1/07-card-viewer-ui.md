# SPEC: Card Viewer UI

**Spec #:** 07  
**Phase:** 1  
**Status:** Done
**Branch:** `feature/p1-07-card-viewer-ui`

---

## Problem

Cards are fetchable via the API (spec #04) and scheduled via FSRS (spec #05),
but there is no screen where a user can actually read a card, test their
knowledge, and record a rating. Without this, the spaced-repetition loop
cannot close: FSRS scheduling produces due dates but nothing lets the user
work through them.

---

## Solution

A `/study/card/:id` route renders a **Card Viewer** for a single card. The
viewer presents a 3D flip card: the **front** shows the question; the **back**
exposes four content tabs — **Concept**, **Production**, **Example**, and
**Quiz**. The Quiz tab is the closure point: the user rates their recall
(Again / Hard / Good / Easy), which fires `POST /api/v1/study/review` and
advances the FSRS state.

---

## Acceptance Criteria

- [ ] **AC-1:** Navigating to `/study/card/:id` fetches the card via
  `GET /api/v1/cards/:id` and renders the question on the card front.

- [ ] **AC-2:** Clicking the card (or a "Flip" button) animates a 3D
  `rotateY` flip revealing the card back. The back defaults to the
  **Concept** tab.

- [ ] **AC-3:** The card back has four tabs: Concept, Production, Example,
  Quiz. Switching tabs does not re-flip the card.

- [ ] **AC-4:** **Concept** tab renders the card's `answer` field as
  formatted markdown text.

- [ ] **AC-5:** **Production** tab renders production-context content
  derived from the answer (highlighted "In production…" sections, or a
  structured "key takeaways" view if the answer is unstructured).

- [ ] **AC-6:** **Example** tab renders any code blocks found in the answer
  in a styled code viewer; falls back to the answer prose if no code blocks
  are present.

- [ ] **AC-7:** **Quiz** tab renders `QuizPanel`. The panel shows the question
  again, a "Reveal Answer" button, and — after reveal — four self-rating
  buttons: **Again (1)**, **Hard (2)**, **Good (3)**, **Easy (4)**.

- [ ] **AC-8:** Clicking a rating button calls `POST /api/v1/study/review`
  with `{ card_id, rating, session_id, time_spent_ms }` and shows the
  resulting `due_date` in a toast ("Next review: in 3 days").

- [ ] **AC-9:** The page fires PostHog event `card_viewed` on mount.
  Quiz reveal fires `quiz_submitted`. Rating submission fires `card_reviewed`.

- [ ] **AC-10:** Navigating to a non-existent card returns an inline 404
  error state with a back-to-dashboard link.

- [ ] **AC-11:** On mobile the card takes full viewport width; tabs stack
  label-only (no icon labels truncated). The flip button is always in the
  viewport.

---

## Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  ← Study Dashboard     System Design  •  medium         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │   FRONT: What is the CAP theorem?                 │  │
│  │                                                   │  │
│  │                         [Flip card ↩]             │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  (after flip)                                           │
│                                                         │
│  ┌─[Concept]─[Production]─[Example]─[Quiz]───────────┐  │
│  │                                                   │  │
│  │   CAP theorem states that a distributed system    │  │
│  │   cannot simultaneously provide Consistency,      │  │
│  │   Availability, and Partition tolerance…          │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### Page: `CardViewer`
**File:** `src/pages/CardViewer.tsx`

- Reads `:id` from `useParams`.
- Fetches `GET /api/v1/cards/:id` via `useCardViewer` hook.
- Manages `isFlipped`, `activeTab`, `sessionStartMs` state.
- Renders `FlipCard`, breadcrumb, difficulty badge.
- Fires `card_viewed` PostHog on mount.

---

### Component: `FlipCard`
**File:** `src/components/study/FlipCard.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `question` | `string` | Card front text |
| `isFlipped` | `boolean` | Controlled flip state |
| `onFlip` | `() => void` | Called when user clicks to flip |
| `backContent` | `ReactNode` | Rendered inside the back face |

Uses CSS `perspective` + Framer Motion `rotateY`. Front and back faces are
absolutely positioned; `backfaceVisibility: 'hidden'` prevents ghost rendering.
Back face is rotated 180° by default and counter-rotated to 0° when flipped.

---

### Component: `QuizPanel`
**File:** `src/components/study/QuizPanel.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `cardId` | `string` | Card being reviewed |
| `question` | `string` | Re-shown during quiz |
| `answer` | `string` | Revealed after user prompt |
| `sessionId` | `string` | FSRS session ID (echoed to review endpoint) |
| `startTimeMs` | `number` | When card was first shown (for time_spent_ms) |
| `onRated` | `(rating: 1\|2\|3\|4, result: ReviewResponse) => void` | Called on successful submit |

States: `idle → revealed → submitting → done`.

Rating buttons map to FSRS labels:
| Button | Rating | Label colour |
|--------|--------|--------------|
| Again | 1 | `text-red-400` |
| Hard | 2 | `text-orange-400` |
| Good | 3 | `text-accent-primary` |
| Easy | 4 | `text-accent-secondary` |

---

### Hook: `useCardViewer`
**File:** `src/hooks/useCardViewer.ts`

```typescript
{
  card: Card | null
  isLoading: boolean
  error: Error | null
}
```

Fetches `GET /api/v1/cards/:id`. 404 is surfaced as an `Error` with
message `"Card not found"`.

---

## API Calls

### 1. `GET /api/v1/cards/:id`
Already specified in spec #04. Returns `Card` with `question`, `answer`,
`difficulty`, `tags`, `category_name`.

### 2. `POST /api/v1/study/review`
Already specified in spec #05.

**Request:**
```json
{
  "card_id": "<UUID>",
  "rating": 3,
  "session_id": "<UUID>",
  "time_spent_ms": 12400
}
```
**Response:** `ReviewResponse` — `fsrs_state`, `due_date`, `scheduled_days`, etc.

`session_id` is generated client-side (crypto.randomUUID()) if the viewer
is accessed directly (not from the daily queue). The daily queue provides its
own `session_id`.

---

## Tab Content Strategy

The backend stores one `answer` field per card. Tab content is derived
client-side without extra API calls:

| Tab | Source |
|-----|--------|
| **Concept** | Full `answer` text rendered as markdown prose |
| **Production** | Lines/paragraphs beginning with "In production", "Tip:", "Note:", "Warning:", bullet lists; falls back to full answer if none found |
| **Example** | Fenced code blocks (``` ``` ```) extracted from `answer`; falls back to full answer prose |
| **Quiz** | Always the interactive `QuizPanel` |

This zero-API approach works for the current schema. When the backend adds
structured `concept`, `production`, `example` fields to cards (future spec),
each tab source switches to the dedicated field with no UI change needed.

---

## Edge Cases

- **Card not found (404):** Show inline error with "← Back to Dashboard" link.
- **Review API fails:** Toast error; rating buttons remain enabled for retry.
- **No code blocks in answer:** Example tab shows full answer prose with note
  "No code examples in this card."
- **Card already reviewed today:** Allow re-review; FSRS handles rating
  on already-reviewed cards (updates state normally).
- **Direct navigation (no session_id):** Generate a new UUID client-side.
- **Mobile flip:** Tap anywhere on the card front to flip; a fixed "Flip ↩"
  button also appears for accessibility.

---

## Dependencies

| Spec | Status |
|------|--------|
| #04 — Cards API (`GET /api/v1/cards/:id`) | Must be done first |
| #05 — FSRS Review (`POST /api/v1/study/review`) | Must be done first |
| #06 — Study Dashboard (back-nav target) | Done |

---

## PostHog Events

| Event | When | Properties |
|-------|------|------------|
| `card_viewed` | Page mount | `{ card_id, category_id, difficulty, fsrs_state? }` |
| `quiz_submitted` | Reveal clicked | `{ card_id, time_to_reveal_ms }` |
| `card_reviewed` | Rating button clicked | `{ card_id, rating, fsrs_state_after, scheduled_days }` |

---

## Test Plan

### Unit tests
- **`FlipCard`:** front face visible when `isFlipped=false`; back face when
  `true`; clicking fires `onFlip`.
- **`QuizPanel` states:** idle → show "Reveal Answer"; revealed → show rating
  buttons; submitting → buttons disabled; done → show due date.
- **`QuizPanel` submit:** correct payload sent (card_id, rating, session_id,
  time_spent_ms > 0); `onRated` called with response.
- **Tab content parsing:** code block extractor returns fenced blocks;
  production-line extractor finds "In production" / "Tip:" prefixes.

### Manual verification
1. Navigate to `/study/card/<valid-id>` — question visible on front.
2. Click card — flips smoothly (≈ 500ms), Concept tab active.
3. Switch tabs — no re-flip; content updates.
4. Open Quiz tab → click "Reveal Answer" — answer appears.
5. Click "Good (3)" — toast shows next review date; network tab shows
   `POST /api/v1/study/review` with `rating: 3`.
6. Navigate to `/study/card/<nonexistent>` — error state shown.
7. On a 375px viewport — card is full width, tabs visible, flip button accessible.
