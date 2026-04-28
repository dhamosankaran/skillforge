---
slug: keyword-density-vs-context
title: Keyword Density vs Contextual Relevance
display_order: 1
quiz_items:
  - question: 'Why is "stuffing" a skills list with every keyword from the job description usually counterproductive?'
    answer: 'Modern ATS engines score on contextual relevance, not raw token count — keywords that appear in a skills list but never in the experience bullets get heavily discounted, and the overall keyword density relative to bullet count flags as suspicious. Recruiters who manually screen catch keyword-stuffed resumes immediately and toss them. Better to integrate keywords naturally inside bullets where they describe what was done.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'A job description requires "Python, distributed systems, Kafka, and on-call experience". The candidate has all four but in different roles. How should the resume position them?'
    answer: 'Surface the four anchor terms in the role-summary lines AND in at least one bullet per term, with concrete artifacts ("co-owned the Kafka ingest pipeline carrying 8B events/day"). Place the most senior demonstration of each term in the most recent role where applicable, and leave a tracked-changes thread of the same term across roles so the parser sees consistent reinforcement. Avoid a top-of-resume "skills" stuffing of all four — recruiters discount that section first.'
    question_type: free_text
    difficulty: hard
    display_order: 1
---
## Concept

ATS keyword scoring used to be naive: count occurrences of the JD's
nouns in the resume, rank by overlap. Modern engines (Greenhouse Goldie,
iCIMS' AI matcher, Workday Skills Cloud) use embedding-based scoring on
context windows around each candidate token, so an ungrounded keyword in
a skills list scores much lower than the same keyword inside a bullet
that describes what was done with it.

The mental model: every keyword wants a job. Don't list it without
giving it work to do.

## Production

Three patterns that maximize signal:

1. **Anchor in the role-summary line.** Each role gets a one-line
   summary; embed the highest-priority keywords from the JD there.
2. **Reinforce in bullets.** Each anchor term shows up in at least one
   bullet with a concrete artifact, scope, or outcome.
3. **Group secondary skills into projects.** Things you've used
   tangentially — Terraform, Datadog, OpenSearch — go in a one-line
   "Tools" trailer or in project descriptions, not the top skills
   section.

```text
Senior Software Engineer, real-time data platform.       ← anchor: Kafka
- Co-owned a 12-broker Kafka cluster ingesting 8B           ← reinforce: Kafka
  events/day across 30 topics; reduced consumer lag p95
  from 4.2s to 380ms by repartitioning the hot topics
  and right-sizing batch.size.
```

The candidate hit "Kafka" twice in the right places. A keyword-stuffed
version would put `Kafka, Kafka Streams, KSQL, Schema Registry, MSK,
Confluent` in a skills line at the top — easy to spot, easy to discount.

## Examples

| Approach                         | ATS score | Recruiter read       |
|----------------------------------|-----------|----------------------|
| Bare skills list of all keywords | Medium    | Stuffed; low signal  |
| Keywords only in bullets         | Medium    | Honest but unscanned |
| Anchor + reinforce + tools strip | High      | Senior, considered    |
| Sprinkle randomly                | Low       | Unfocused            |

The discipline is treating the resume as a small information-retrieval
system: indexed by ATS, ranked by recruiter, and clicked-through to
interview by hiring manager. Each keyword needs to earn its position.
