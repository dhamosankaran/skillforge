# Claude Code Prompt: Install SkillForge Design System + Landing Page

Copy-paste this entire prompt into Claude Code:

---

```
Read AGENTS.md. Read CLAUDE.md.

I'm installing a new design system and landing page for SkillForge. I have two files ready to drop in. Here's what I need you to do:

/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/LandingPage.tsx
/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/design-tokens.css

STEP 1 — FONT INSTALLATION:

1. Add these Google Fonts CDN links to index.html (or the appropriate place in the Vite setup):
   - Cabinet Grotesk (display font): https://api.fontshare.com/v2/css?f[]=cabinet-grotesk@400,500,700,800&display=swap
   - General Sans (body font): https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700&display=swap
   
   These are from Fontshare (free for commercial use). Add as <link> tags in index.html.

2. Add JetBrains Mono for code/monospace: https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap

STEP 2 — DESIGN TOKENS:

1. Create src/styles/design-tokens.css with the SkillForge "Midnight Forge" design system.
   I'll paste the content — it defines CSS custom properties for colors, typography, spacing, 
   and utility classes. The theme is:
   - Background: Deep void (#06060A) 
   - Accent: Electric cyan (#00D4FF) → Purple (#7B61FF) → Warm amber (#FF8A50)
   - Cards: Slightly lifted dark surfaces with subtle borders
   - CTAs: Cyan-to-purple gradient with glow
   
2. Import the design tokens in main.tsx: import './styles/design-tokens.css'

3. Update the global body styles to use the new design tokens.

STEP 3 — LANDING PAGE:

1. Create src/pages/LandingPage.tsx with the new landing page component I'll paste.
   
   The page has 8 sections:
   - Navbar (glassmorphism on scroll)
   - Hero (gradient text, dual CTA, grid background)
   - Logo bar (social proof — company names)
   - The Loop (scan → gaps → study → ace — 4 cards)
   - Three Engines (Lens, Forge, Mission — 3 feature cards)
   - How It Works (3-step numbered flow)
   - Pricing (Free vs Pro side-by-side)
   - Final CTA + Footer
   
2. Uses framer-motion for scroll-triggered animations. Make sure framer-motion is installed.

3. Update the route in App.tsx:
   - "/" should render LandingPage when user is NOT logged in
   - "/" should redirect to /study when user IS logged in

STEP 4 — CLEANUP:

1. Remove the old HireLens/HirePort landing page or home page component (if it exists).
2. Update any navigation links that pointed to the old home page.
3. Make sure the navbar "Log in" and "Scan Free" buttons link to /login.
4. Make sure the pricing "Get started free" and "Start Pro" buttons link to /login.

STEP 5 — VERIFY:

1. Run: npm run dev -- --port 5199
2. Check that the landing page loads at http://localhost:5199
3. Check that the dark theme looks correct (no white flashes, no unstyled content)
4. Check that scroll animations trigger on each section
5. Check that the navbar goes translucent with blur on scroll
6. Check mobile responsiveness (resize browser to 375px width)
7. Run: npx vitest run (existing tests still pass)

Do NOT change any other pages or components. This is a landing page + design tokens install only.

After verification, commit:
git add -A && git commit -m "feat(ui): install Midnight Forge design system + new landing page"
```

---

## Font Fallback Note

The fonts above are from Fontshare (free, no API key needed). If they don't load in development:
- Cabinet Grotesk → falls back to system-ui sans-serif
- General Sans → falls back to system-ui sans-serif
- JetBrains Mono → falls back to Fira Code or monospace

The design still works with fallbacks — the custom fonts are polish, not structural.

## What to Review After Claude Code Runs

1. Does the hero gradient text ("Start forging.") render with the cyan→purple→amber gradient?
2. Does the navbar blur on scroll?
3. Do the cards in "The Loop" section have subtle colored bottom borders?
4. Does the Pro pricing card have a cyan glow border?
5. Is the "MOST POPULAR" badge positioned above the Pro card?
6. On mobile (375px), does everything stack cleanly?

If any section looks off, tell Claude Code:
"The [section name] section has [specific issue]. Fix it without changing other sections."
