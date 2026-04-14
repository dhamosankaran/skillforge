---
description: IP-based geo pricing (INR vs USD) with Redis caching and Stripe price ID routing
---
# Geo Pricing Skill

## Overview
Pro pricing is localized by visitor IP. Indian visitors see **₹999/mo**
billed in INR; everyone else sees **$49/mo** billed in USD. The mapping
is served by a single backend endpoint backed by `ip-api.com` for
geolocation and Redis for caching; the frontend reads it through
`usePricing()` and feeds the currency into Stripe checkout.

## Key Files
- Backend: `app/services/geo_pricing_service.py`
- Route: `GET /api/v1/payments/pricing` (in `app/api/v1/routes/payments.py`)
- Frontend hook: `src/hooks/usePricing.ts`
- Used by: `src/pages/LandingPage.tsx`, `src/components/PaywallModal.tsx`

## Geolocation
- Provider: **ip-api.com** (free tier, no API key, 45 req/min limit)
- Call: `GET http://ip-api.com/json/{ip}?fields=status,countryCode`
- Returns `countryCode` (ISO-3166-1 alpha-2), e.g. `IN`, `US`, `GB`.
- Failure modes (timeout, rate limit, bad IP) → fall through to USD.

## Pricing Rules

| Country | Currency | Price | Stripe price ID env var |
|---------|----------|-------|-------------------------|
| `IN` | INR | ₹999/mo | `STRIPE_PRO_PRICE_ID_INR` |
| everything else | USD | $49/mo | `STRIPE_PRO_PRICE_ID` |

The service returns:
```json
{
  "currency": "inr" | "usd",
  "price": 999 | 49,
  "price_display": "₹999/mo" | "$49/mo",
  "stripe_price_id": "price_..."
}
```

## Redis Caching
- Key: `geo_pricing:{ip_address}`
- TTL: **86400 seconds** (24 hours)
- Value: the JSON dict above, serialized.
- On Redis outage the service still returns the correct pricing —
  Redis is a performance layer, not a correctness layer.

## Environment Variables
| Variable | Purpose |
|----------|---------|
| `STRIPE_PRO_PRICE_ID` | Stripe USD monthly price id |
| `STRIPE_PRO_PRICE_ID_INR` | Stripe INR monthly price id |
| `REDIS_URL` | Used for the pricing cache |

## Frontend Integration

```ts
// src/hooks/usePricing.ts
const { pricing, isLoading } = usePricing()
//  pricing.price_display  -> "₹999/mo" or "$49/mo"
//  pricing.currency       -> "inr" | "usd"
//  pricing.price          -> numeric amount (major units)
```

- `LandingPage.tsx` renders `pricing.price_display` in the plans table.
- `PaywallModal.tsx` renders `pricing.price_display` in the CTA and
  passes `pricing.currency` to `createCheckoutSession(currency)` so
  the Stripe Checkout Session uses the matching price id.
- Defaults: `{price: 49, price_display: '$49/mo', currency: 'usd'}`
  until the fetch resolves, so there is no placeholder flicker.

## Rules
- **Never** hardcode a price in the frontend or in any marketing
  component — always go through `usePricing()`.
- When adding a new currency, add a column to the pricing map in
  `geo_pricing_service.py`, add a new Stripe price id env var, and
  update this skill file.
- Do **not** cache by country code alone — IPs can move between
  countries; cache by IP so TTL expiry re-checks correctly.
