---
description: "Activate peer code reviewer persona to review code changes before committing"
---

# Peer Code Review

## When to Use
After implementing a feature slice and before `git commit`.

## Prompt Template

```
Put on your Senior Engineer / Peer Reviewer hat.

Review the changes I just made. Check for:

1. **Correctness**: Does the code actually do what the spec says?
   - Read the spec: docs/specs/phase-X/NN-feature.md
   - Verify each Acceptance Criterion is met

2. **Security**: Any auth bypasses, SQL injection, XSS, leaked secrets?
   - All routes have `Depends(get_current_user)`?
   - All user input validated via Pydantic?

3. **Testing**: Are the tests meaningful (not tautological)?
   - Tests assert BEHAVIOR, not implementation details
   - Edge cases covered (empty input, unauthorized, plan limits)

4. **Conventions**: Does this follow AGENTS.md coding conventions?
   - Backend: async, Pydantic v2, SQLAlchemy 2.0 style
   - Frontend: functional components, useQuery pattern
   - Naming: snake_case (Python), PascalCase (components)

5. **Performance**: Any obvious N+1 queries, missing indexes, memory leaks?

6. **Simplicity**: Could this be simpler? Is there dead code?

Give me APPROVE / REQUEST CHANGES with specific line-level feedback.
```

## Expected Output Format

```
## Peer Review: [Feature/File]

**Verdict: APPROVE ✅ / REQUEST CHANGES 🔄**

### Issues Found
1. [severity: critical/medium/nit] [file:line] — description
2. ...

### What Looks Good
- ...

### Suggested Improvements (Optional)
- ...
```
