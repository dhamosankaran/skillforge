---
slug: star-storytelling
title: STAR Storytelling
display_order: 0
quiz_items:
  - question: 'What does each letter of STAR stand for, and which letter do candidates most often under-invest in?'
    answer: 'Situation, Task, Action, Result. Candidates over-invest in Situation (long context-setting) and under-invest in Action — the part where the interviewer is grading what YOU specifically did. Strong answers compress S+T into 30 seconds and spend 60-90 seconds on Action with concrete decisions, trade-offs, and what changed because of you.'
    question_type: free_text
    difficulty: easy
    display_order: 0
  - question: 'A story has Situation/Task/Action/Result but consistently bombs in mock interviews. What are the most likely fixes?'
    answer: 'The most common cause is "we" disease — the candidate narrates the team''s actions instead of their own, leaving the interviewer unsure what to credit them for. Fix: rewrite Action in first-person ("I argued for X because Y"). Other fixes: lead with the Result so the interviewer knows where the story is going; cut filler from Situation; make trade-offs explicit ("we considered X and Y; I chose Y because Z").'
    question_type: free_text
    difficulty: medium
    display_order: 1
---
## Concept

STAR (Situation, Task, Action, Result) is the structure interviewers
recognize. It works because behavioral questions are asking for
evidence that you operate at a level, and stories with explicit
structure make evidence easy to grade.

The senior version of STAR is STAR-with-trade-offs: every Action step
calls out a decision, the alternatives considered, and why this one
won. That's the part that signals seniority — junior candidates list
what they did; senior candidates explain why it was the right call
given the constraints.

## Production

The 90-second STAR template:

- **Situation** (10-20s). One sentence on context. "We had a 15-second
  p99 on the search endpoint and Q3 SLA was 2 seconds."
- **Task** (5-10s). What you owned. "I was the tech lead on the
  perf-fix sprint."
- **Action** (50-70s). What you specifically did, in 3-4 beats with
  trade-offs called out. "I profiled and saw the bottleneck was
  the unindexed scan. I argued against the obvious add-an-index fix
  because it would lock the table for an hour at our row count, and
  proposed a CONCURRENTLY build with a feature-flag rollout. We
  shipped behind 1% / 10% / 100% gates over a week."
- **Result** (10-20s). Quantified outcome. "p99 dropped from 15s to
  380ms. SLA held through Q3. The pattern became our default for
  online schema changes."

Common failure modes: stories where the interviewer can't tell what
the candidate did personally, stories with no quantified result, and
stories where the trade-off was so obvious that "I made the right
choice" carries no signal.

## Examples

| Question                              | Story to use                          |
|---------------------------------------|---------------------------------------|
| Tell me about a time you disagreed    | Pick a technical disagreement with a peer where you changed someone's mind on data, not authority |
| Tell me about a difficult bug         | The one where the obvious answer was wrong and the second-order debugging mattered |
| Tell me about a project that failed   | Pick one where the failure taught a real lesson; do not pick a story where the lesson is "I learned to communicate" |
| Tell me about scaling a team          | Pick a hire-and-grow arc, not a hire-and-fire arc |

The skill is having 6-10 stories prepped that map to the dozen
canonical questions, then choosing the right story for the question
under pressure rather than free-styling.
