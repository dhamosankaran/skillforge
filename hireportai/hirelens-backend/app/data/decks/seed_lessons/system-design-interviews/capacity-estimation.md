---
slug: capacity-estimation
title: Capacity Estimation in System Design Interviews
display_order: 0
quiz_items:
  - question: 'Walk through the back-of-envelope math for QPS of a service with 100M DAU, where the average user issues 5 reads and 0.5 writes per session and there are 2 sessions per day.'
    answer: 'Reads/day = 100M × 5 × 2 = 1B reads. Writes/day = 100M × 0.5 × 2 = 100M writes. Average = 1.1B / 86,400s ≈ 12.7K QPS combined; 11.5K read QPS, 1.16K write QPS. Peak is typically 2-3× average, so plan for ~30-40K read QPS and ~3K write QPS.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Which is the right order to derive capacity numbers in an interview?'
    answer: 'Users → traffic → storage → bandwidth → memory'
    question_type: mcq
    distractors:
      - 'Storage → memory → users → traffic → bandwidth'
      - 'Bandwidth → traffic → users → storage → memory'
      - 'Memory → bandwidth → users → storage → traffic'
    difficulty: easy
    display_order: 1
---
## Concept

Capacity estimation is the part of system design where weak candidates
guess and strong candidates derive. Five quantities to put on the
whiteboard, in order: users (DAU), traffic (QPS), storage (TB),
bandwidth (Gbps), memory (RAM for hot set).

The discipline is to write down assumptions, do simple arithmetic, and
keep precision honest — "12.7K QPS" is fine; "12,742 QPS" is comedy.
Round numbers signal you know what your error bars are.

## Production

The interview script:

1. **Users.** "Let's say 100M DAU." Write it down.
2. **Sessions and actions.** "2 sessions/day, 5 reads + 0.5 writes per
   session." Multiply.
3. **Total per day.** Reads = 1B, writes = 100M. Divide by 86400 to get
   QPS.
4. **Peak factor.** "Peak is 2-3× average."
5. **Storage.** "Each write produces ~1KB of data." → 100M × 1KB = 100GB
   per day; ×365 = 36TB/year.
6. **Read pattern → cache sizing.** "80/20 rule: 80% of reads hit 20%
   of items." Top-of-mind set fits in RAM if it's <500GB.

## Examples

| Service       | DAU   | Reads/user | Writes/user | Peak QPS  |
|---------------|-------|------------|-------------|-----------|
| Twitter feed  | 200M  | 30         | 1           | ~700K     |
| Slack channel | 30M   | 100        | 5           | ~350K     |
| Stripe API    | 5M    | 0.1        | 0.05        | ~30 QPS   |

The point isn't the numbers — it's that the candidate can re-derive
them under pressure when the interviewer says "what if DAU doubles?"
