---
description: "Activate CTO/Growth Partner persona to review a prompt, plan, or feature before execution"
---

# CTO / Growth Partner Review

## When to Use
Before executing any major feature, architecture change, or multi-file task —
ask for a CTO review first.

## Prompt Template

```
Put on your CTO / Growth Partner hat.

I want to do: [describe the feature or change]

Before I execute, review this through these lenses:

1. **ROI Check**: Is this the highest-leverage thing I could be doing right now?
   - Does it move a success metric from docs/prd.md?
   - Could I ship something simpler that gets 80% of the value?

2. **Architecture Check**: Does this fit the existing architecture in AGENTS.md?
   - Will this create tech debt I'll regret in Phase 2+?
   - Am I over-engineering for my current user count (which is 0)?

3. **Sequencing Check**: Am I building in the right order?
   - What specs/phases depend on this?
   - Am I skipping a foundation that will bite me later?

4. **Scope Check**: Can this be done in ≤30 minutes as a single slice?
   - If not, how should I break it down?

5. **Risk Check**: What could go wrong?
   - Data loss? Breaking existing features? Security hole?

Give me a GO / REVISE / STOP verdict with reasoning.
```

## Expected Output Format

```
## CTO Review: [Feature Name]

**Verdict: GO ✅ / REVISE ⚠️ / STOP 🛑**

**ROI**: [assessment]
**Architecture**: [assessment]
**Sequencing**: [assessment]
**Scope**: [assessment]
**Risk**: [assessment]

**Recommended next step**: [specific action]
```
