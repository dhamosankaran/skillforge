"""Smoke test for Stripe Customer Portal configuration + session creation.

Diagnostic for E-033 (billing portal fails with opaque "Couldn't open
billing portal"). Probes two things, in order, and prints a clear
PASS/FAIL with diagnostic details:

  CHECK 1 — Portal configuration exists.
    Calls ``stripe.billing_portal.Configuration.list(limit=5)``. If the
    returned collection is empty → Stripe Dashboard default Customer
    Portal configuration has never been saved. This is the primary
    E-033 hypothesis (see docs/investigations/E-033-*.md §4).

  CHECK 2 — Session creation round-trip (optional, requires --customer).
    Calls ``stripe.billing_portal.Session.create(customer=..., return_url=...)``.
    On success, asserts the response shape matches what
    ``app/services/payment_service.py::create_billing_portal_session``
    expects. Optionally performs a plain ``urllib`` GET against the
    returned URL to verify it resolves (no browser automation).

SAFETY:
  - Defaults to test mode. Refuses to run unless ``STRIPE_SECRET_KEY``
    begins with ``sk_test_``. To run against live mode, pass both
    ``--live`` and ``--yes-live`` and type the confirmation phrase.
  - Read-only against the Stripe account EXCEPT when --customer is
    provided, in which case a portal session is created (Stripe auto-
    expires these; no user-visible side effect).
  - Does not touch the application database.
  - Does not mutate Stripe objects beyond the Session.create idempotent
    fetch.

Usage:
    # Check 1 only — verify config exists in test mode
    python scripts/smoke_billing_portal.py

    # Check 1 + Check 2 — create a session for an existing test customer
    python scripts/smoke_billing_portal.py --customer cus_TEST_xxx

    # Against live mode (requires double confirmation)
    python scripts/smoke_billing_portal.py --live --yes-live \\
        --customer cus_LIVE_xxx

Exit codes:
    0  PASS — every requested check succeeded.
    1  FAIL — a configuration or setup problem (Check 1 failed, or
       mode/key mismatch).
    2  FAIL — Stripe API call raised an error (Check 2 failed, or
       Configuration.list() errored).
    3  FAIL — something else (bad args, missing env, unexpected).

Env vars read:
    STRIPE_SECRET_KEY — required (from .env via python-dotenv).
    FRONTEND_URL       — optional; used as the portal return_url when
                         --customer is passed. Defaults to
                         http://localhost:5199.

Related:
    docs/investigations/E-033-billing-portal-2026-04-21.md — the
        investigation report that motivated this script.
    docs/diagnostics/E-033-stripe-dashboard-checklist-2026-04-21.md —
        the Dashboard-side checklist to run alongside this script.
    app/services/payment_service.py::create_billing_portal_session —
        the production code path this script probes.
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from typing import Any

try:
    import stripe
except ImportError:
    sys.stderr.write(
        "stripe library is not installed. Run from inside the backend venv:\n"
        "  cd hirelens-backend && source venv/bin/activate\n"
    )
    sys.exit(3)

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional; if missing, rely on the ambient environment.
    def load_dotenv() -> bool:  # type: ignore[misc]
        return False


LIVE_CONFIRMATION_PHRASE = "i confirm live mode"
DEFAULT_RETURN_URL = "http://localhost:5199/profile"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "E-033 diagnostic: verify Stripe Customer Portal config + "
            "session creation."
        )
    )
    p.add_argument(
        "--customer",
        metavar="CUSTOMER_ID",
        default=None,
        help=(
            "Stripe customer id (e.g. cus_xxx) to create a portal session "
            "for. When omitted, only Check 1 (configuration list) runs."
        ),
    )
    p.add_argument(
        "--live",
        action="store_true",
        help=(
            "Run against live mode. Requires --yes-live and an interactive "
            "confirmation. Default is test mode."
        ),
    )
    p.add_argument(
        "--yes-live",
        action="store_true",
        help=(
            "Confirms you intend live mode. Still requires typing the "
            f"exact phrase {LIVE_CONFIRMATION_PHRASE!r} when prompted."
        ),
    )
    p.add_argument(
        "--fetch-url",
        action="store_true",
        help=(
            "When --customer is set, issue a plain GET to the returned "
            "portal URL and assert HTTP 200. Useful for confirming the "
            "session URL is reachable (does NOT log in)."
        ),
    )
    p.add_argument(
        "--return-url",
        default=None,
        metavar="URL",
        help=(
            f"Return URL sent to Stripe. Defaults to FRONTEND_URL env + "
            f"'/profile', falling back to {DEFAULT_RETURN_URL!r}."
        ),
    )
    return p.parse_args()


def require_mode(key: str, want_live: bool, yes_live: bool) -> int | None:
    """Validate the Stripe key matches the requested mode.

    Returns an exit code on failure, or ``None`` on success.
    """
    if not key:
        sys.stderr.write(
            "FAIL: STRIPE_SECRET_KEY is not set. Load .env or export it.\n"
        )
        return 1

    is_test = key.startswith("sk_test_")
    is_live = key.startswith("sk_live_") or key.startswith("rk_live_")

    if not is_test and not is_live:
        sys.stderr.write(
            f"FAIL: STRIPE_SECRET_KEY has an unexpected prefix "
            f"({key[:8]!r}...). Expected sk_test_ or sk_live_.\n"
        )
        return 1

    if want_live and is_test:
        sys.stderr.write(
            "FAIL: --live was passed but STRIPE_SECRET_KEY is a test key.\n"
        )
        return 1
    if not want_live and is_live:
        sys.stderr.write(
            "FAIL: STRIPE_SECRET_KEY is a live key but --live was not "
            "passed. Refusing to run against live mode by default.\n"
        )
        return 1

    if want_live:
        if not yes_live:
            sys.stderr.write(
                "FAIL: --live requires --yes-live as a second opt-in.\n"
            )
            return 1
        sys.stdout.write(
            f"LIVE MODE requested. Type {LIVE_CONFIRMATION_PHRASE!r} to "
            f"proceed (anything else aborts): "
        )
        sys.stdout.flush()
        typed = sys.stdin.readline().strip().lower()
        if typed != LIVE_CONFIRMATION_PHRASE:
            sys.stderr.write("Aborted — confirmation phrase not matched.\n")
            return 1
        print("Live-mode confirmation accepted.")

    mode = "LIVE" if want_live else "TEST"
    print(f"Mode: {mode} (key prefix={key[:8]}...)")
    return None


def check_configuration_exists() -> int | None:
    """CHECK 1 — list Customer Portal configurations.

    Empty list → primary E-033 hypothesis confirmed: Dashboard default
    Customer Portal configuration has never been saved. Dhamo must go
    to dashboard.stripe.com/{test/,}settings/billing/portal and save
    the default config once.

    Returns an exit code on failure, or ``None`` on success.
    """
    print("\n--- CHECK 1: Customer Portal configuration exists ---")
    try:
        configs = stripe.billing_portal.Configuration.list(limit=5)
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        sys.stderr.write(
            f"FAIL (Check 1): Stripe API error listing configurations: "
            f"{exc}\n"
        )
        return 2

    data = getattr(configs, "data", []) or []
    if not data:
        sys.stderr.write(
            "FAIL (Check 1): No billing portal configurations found.\n"
            "  This is the primary E-033 hypothesis: the Stripe Dashboard\n"
            "  default Customer Portal configuration has never been saved.\n"
            "  Fix: open dashboard.stripe.com/test/settings/billing/portal\n"
            "  (or the live equivalent), review the default configuration,\n"
            "  and click Save. Re-run this script to confirm.\n"
        )
        return 1

    default_ids = [c.id for c in data if getattr(c, "is_default", False)]
    print(f"OK (Check 1): {len(data)} configuration(s) found.")
    for c in data:
        is_default = getattr(c, "is_default", False)
        active = getattr(c, "active", None)
        print(
            f"  - id={c.id}  is_default={is_default}  active={active}"
        )
    if not default_ids:
        sys.stderr.write(
            "WARN (Check 1): No configuration is marked is_default=True.\n"
            "  Stripe falls back to the most-recently-updated active one,\n"
            "  but an explicit default is recommended.\n"
        )
    return None


def resolve_return_url(arg_return_url: str | None) -> str:
    if arg_return_url:
        return arg_return_url
    frontend = os.getenv("FRONTEND_URL")
    if frontend:
        return f"{frontend.rstrip('/')}/profile"
    return DEFAULT_RETURN_URL


def check_session_creation(
    customer_id: str,
    return_url: str,
    fetch_url: bool,
) -> int | None:
    """CHECK 2 — create a portal session for the given customer.

    Mirrors the production call shape in
    ``payment_service.create_billing_portal_session``. On success,
    optionally performs a GET against the session URL to verify
    reachability.

    Returns an exit code on failure, or ``None`` on success.
    """
    print("\n--- CHECK 2: Session creation round-trip ---")
    print(f"  customer={customer_id}")
    print(f"  return_url={return_url}")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        sys.stderr.write(
            f"FAIL (Check 2): Stripe API error creating portal session: "
            f"{exc}\n"
            "  If the error mentions 'No configuration provided' or "
            "'default configuration has not been created', Check 1 was "
            "a false positive — re-check Dashboard config.\n"
        )
        return 2

    url = getattr(session, "url", None)
    session_id = getattr(session, "id", None)
    if not url or not session_id:
        sys.stderr.write(
            f"FAIL (Check 2): response shape unexpected "
            f"(url={url!r}, id={session_id!r}).\n"
        )
        return 2

    print(f"OK (Check 2): session created.")
    print(f"  id={session_id}")
    print(f"  url={url}")

    if fetch_url:
        return _check_url_reachable(url)
    return None


def _check_url_reachable(url: str) -> int | None:
    """Optional Check 2b — plain GET the portal URL.

    Returns an exit code on failure, or ``None`` on success.
    """
    print("\n--- CHECK 2b: Portal URL reachable (HTTP GET) ---")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "smoke-billing-portal/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            status = resp.status
    except urllib.error.HTTPError as exc:
        sys.stderr.write(
            f"FAIL (Check 2b): portal URL returned HTTP {exc.code}.\n"
        )
        return 2
    except urllib.error.URLError as exc:
        sys.stderr.write(
            f"FAIL (Check 2b): could not reach portal URL: {exc.reason}\n"
        )
        return 2

    if status != 200:
        sys.stderr.write(
            f"FAIL (Check 2b): expected HTTP 200, got {status}.\n"
        )
        return 2
    print(f"OK (Check 2b): HTTP 200 from portal URL.")
    return None


def main() -> int:
    try:
        args = parse_args()
    except SystemExit as exc:
        return int(exc.code or 3)

    load_dotenv()
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    fail = require_mode(key, want_live=args.live, yes_live=args.yes_live)
    if fail is not None:
        return fail

    stripe.api_key = key

    fail = check_configuration_exists()
    if fail is not None:
        return fail

    if args.customer:
        return_url = resolve_return_url(args.return_url)
        fail = check_session_creation(
            customer_id=args.customer,
            return_url=return_url,
            fetch_url=args.fetch_url,
        )
        if fail is not None:
            return fail
    else:
        print(
            "\nSkipping Check 2 (no --customer passed). Pass "
            "--customer cus_xxx to exercise session creation against a "
            "real test-mode customer."
        )

    print("\nPASS — all requested checks succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
