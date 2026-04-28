---
slug: building-ml-orgs
title: Building ML and AI Engineering Organizations
display_order: 1
quiz_items:
  - question: 'A startup is hiring its first three AI engineers. What roles should they hire — and in what order?'
    answer: 'First hire: a generalist AI engineer who can stand up evals, ship a working RAG pipeline, and own the production observability story end-to-end. Second hire: a complementary specialist depending on bottleneck — applied scientist if the quality bar requires fine-tuning or eval-methodology depth, infrastructure engineer if inference cost / latency is dominating the roadmap. Third hire: the second of whichever the second hire wasn''t, plus deliberate diversity (at least one engineer who challenges the founders'' biases on the product). The anti-pattern: hiring three "AI researchers" before there is an eval suite or a deployment pipeline.'
    question_type: free_text
    difficulty: hard
    display_order: 0
  - question: 'A reasonable first-90-days deliverable for the first AI engineer hire is best described as which of the following?'
    answer: 'A working production deployment plus an eval suite with at least three tracked metrics'
    question_type: mcq
    distractors:
      - 'A research paper on the team''s prompt-engineering technique'
      - 'A custom-trained model fine-tuned on the company''s data'
      - 'A migration of the codebase to a new ML framework'
    difficulty: easy
    display_order: 1
---
## Concept

AI/ML organizations have a different growth shape than classical
software teams. The work spans product engineering, applied research,
infrastructure, and data — and any one of those becoming the
bottleneck stalls the team. Building the org well means hiring the
discipline you're missing, not the discipline you're most comfortable
with.

The senior leader's job is reading the bottleneck and hiring against
it: a quality bottleneck wants applied science; a cost / latency
bottleneck wants inference engineering; a velocity bottleneck wants
generalist AI engineers; a data bottleneck wants ML platform.

## Production

The first-five-hires playbook for an AI-heavy team:

1. **Generalist AI engineer.** Owns evals, deployment, observability.
   Ships a working pipeline in 90 days.
2. **Specialist matching the bottleneck.** Applied scientist if quality
   is the bar; inference engineer if cost / latency is the bar.
3. **Second generalist.** De-risks the bus factor; ideally
   complementary perspective on the product.
4. **Data / ML platform engineer.** When the team starts maintaining
   more than two pipelines or any custom training code.
5. **Domain specialist.** Hire someone who deeply understands the
   problem domain (legal, healthcare, code) once the technical
   foundation is in place.

Three patterns that hold up:

- **Evals before research.** A team without an eval suite cannot
  measure whether research is winning. Build the eval surface as the
  generalist's first deliverable.
- **Deployment from day one.** Hire engineers who deploy what they
  build. Work that lives in notebooks doesn't compound.
- **Cross-functional pairing.** AI engineers should pair regularly
  with domain experts (PM, customer success, support). The most
  common AI failure mode is a model that's technically correct but
  product-irrelevant.

## Examples

| Org bottleneck          | Hire next                         |
|-------------------------|-----------------------------------|
| "Quality isn't there"    | Applied scientist + better evals  |
| "Cost is too high"       | Inference engineer                |
| "We can't ship fast"     | Generalist engineer + tooling     |
| "Models go stale fast"   | ML platform / data engineer       |
| "Reviews keep failing"   | Domain expert + safety review     |

The leader's discipline is naming the bottleneck before opening the
req, then hiring against it. Defaults to comfort hires (more
generalists) without that diagnosis are how AI teams stall.
