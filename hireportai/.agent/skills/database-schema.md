---
description: Living reference of all database tables, columns, types, indexes, and relationships
---

# Database Schema Skill

## Overview
This is the single source of truth for the SkillForge database schema.
Update this file whenever you add or modify a table. Claude Code should
read this before creating any new model or migration to avoid conflicts
and ensure naming consistency.

## Conventions
- All tables use `snake_case` names
- Primary keys: `id` column, type `VARCHAR(36)` (UUID as string — deferred promotion to native UUID)
- Timestamps: `created_at`, `updated_at` — timezone-naive `DateTime()` (deferred promotion to TIMESTAMPTZ)
- Foreign keys: `{related_table}_id` naming pattern
- Soft deletes: NOT used. Hard delete only.
- All tables inherit from `Base` in `app/models/base.py`

## Tables by Phase

### Phase 0 (Foundation)

**users**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | UUID string |
| email | String(255) UNIQUE | No | |
| name | String(255) | Yes | |
| picture | String(500) | Yes | Google profile pic URL |
| role | String(20) | No | "user" or "admin", default "user" |
| plan | String(20) | No | "free" or "pro", default "free" |
| stripe_customer_id | String(255) | Yes | Set after first Stripe checkout |
| google_id | String(255) | Yes | Google OAuth sub |
| created_at | DateTime | No | |
| updated_at | DateTime | No | |

**Existing HireLens tables** (tracker_entries, resumes, etc.)
- See `app/models/` for current definitions
- These predate SkillForge — don't modify unless spec requires it

### Phase 1 (Study Engine)

**categories**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| name | String(100) | No | e.g., "RAG Architecture" |
| icon | String(10) | Yes | Emoji |
| color | String(7) | Yes | Hex color |
| display_order | Integer | No | Sort order |
| source | String(20) | Yes | "foundation" = free tier visible |
| tags | JSON | Yes | Array of tag strings for gap matching |
| created_at | DateTime | No | |

**cards**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| category_id | VARCHAR(36) FK → categories | No | |
| question | Text | No | |
| answer | Text | No | |
| difficulty | String(20) | No | "Easy", "Medium", "Hard" |
| tags | JSON | Yes | Array of tag strings |
| embedding | Vector(1536) | Yes | pgvector for semantic search |
| created_at | DateTime | No | |
| updated_at | DateTime | No | |

**card_progress**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users | No | |
| card_id | VARCHAR(36) FK → cards | No | |
| stability | Float | No | FSRS stability |
| difficulty_fsrs | Float | No | FSRS difficulty (not card difficulty) |
| due_date | DateTime | Yes | Next review date |
| state | String(20) | No | new/learning/review/relearning |
| reps | Integer | No | Total review count |
| lapses | Integer | No | Times "Again" was pressed |
| last_reviewed | DateTime | Yes | |
| created_at | DateTime | No | |
| updated_at | DateTime | No | |
| **UNIQUE** | (user_id, card_id) | | One progress record per user per card |

### Phase 2 (Gamification + Mission)

**gamification_stats**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users UNIQUE | No | |
| current_streak | Integer | No | Default 0 |
| longest_streak | Integer | No | Default 0 |
| total_xp | Integer | No | Default 0 |
| last_active_date | Date | Yes | Calendar date of last activity |

**badges** (reference table — seeded, not user-created)
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| name | String(100) | No | e.g., "7-Day Streak" |
| description | String(255) | No | |
| icon | String(10) | Yes | Emoji |
| threshold_type | String(50) | No | "streak", "xp", "cards_studied" |
| threshold_value | Integer | No | e.g., 7 for "7-Day Streak" |

**user_badges**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users | No | |
| badge_id | VARCHAR(36) FK → badges | No | |
| earned_at | DateTime | No | |
| **UNIQUE** | (user_id, badge_id) | | |

**missions**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users | No | |
| target_date | Date | No | Interview/goal date |
| category_ids | JSON | No | Array of category IDs |
| daily_target | Integer | No | Cards per day |
| status | String(20) | No | active/completed/abandoned |
| created_at | DateTime | No | |

**mission_days**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| mission_id | VARCHAR(36) FK → missions | No | |
| day_number | Integer | No | 1-indexed |
| date | Date | No | |
| cards_target | Integer | No | |
| cards_completed | Integer | No | Default 0 |

**email_preferences**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users UNIQUE | No | |
| daily_reminder | Boolean | No | Default True |
| timezone | String(50) | No | Default "UTC" |

### Phase 3 (Content + Feedback)

**card_feedback**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users | No | |
| card_id | VARCHAR(36) FK → cards | No | |
| rating | Integer | No | 1-5 |
| comment | Text | Yes | |
| created_at | DateTime | No | |

**user_experiences**
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | VARCHAR(36) PK | No | |
| user_id | VARCHAR(36) FK → users | No | |
| content | Text | No | Generated narrative |
| categories_snapshot | JSON | Yes | Frozen stats at generation time |
| generated_at | DateTime | No | |

## Indexes
- `cards.category_id` — FK index (auto)
- `cards.embedding` — ivfflat or hnsw index for pgvector search (add when card count > 1000)
- `card_progress.(user_id, card_id)` — unique composite
- `card_progress.(user_id, due_date)` — for Daily 5 query
- `gamification_stats.user_id` — unique
- `missions.(user_id, status)` — for active mission lookup

## Relationships
- User → many CardProgress, many Missions, one GamificationStats, one EmailPreference
- Category → many Cards
- Card → many CardProgress, many CardFeedback
- Mission → many MissionDays
- Badge → many UserBadges