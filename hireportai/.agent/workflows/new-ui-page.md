---
description: How to add a frontend page
---
## Steps
1. Create page in `src/pages/FeatureName.tsx`
2. Add route in `App.tsx`
3. Add API client method in `services/api.ts`
4. Add PostHog `capture()` on key user interactions
5. Use `useQuery`/`useMutation` for data fetching
6. Mobile-first, dark mode default
7. Write Vitest + RTL test
8. Run: `npx vitest run`
