"""Route-level tests for resume rewrite endpoints (spec #51).

Covers AC-4 (per-section regenerate endpoint returns only target section)
and AC-5 (structured 502 error envelope on truncated/malformed LLM response).
The service-level ACs (AC-1, AC-2, AC-3) live in
tests/services/test_resume_rewrite.py — same mock-the-LLM pattern.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    """Plain AsyncClient — rewrite routes don't depend on the DB."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _echo_title_mock():
    """Mirror of the service-test mock: echo the prompted title back in JSON."""
    import re as _re

    def fake(*, task, prompt, **kwargs):
        m = _re.search(r"Section title \(return verbatim\): (.+)", prompt)
        title = m.group(1).strip() if m else "Unknown"
        return json.dumps({
            "title": title,
            "content": f"Rewritten {title.lower()}.",
            "entries": [],
        })

    return fake


# ─── AC-4: per-section regenerate endpoint ─────────────────────────────────

async def test_ac4_rewrite_section_returns_only_target_section(client):
    """AC-4 — POST /rewrite/section returns exactly one rewritten section."""
    payload = {
        "section_id": "sec-2",
        "section_title": "Experience",
        "section_text": "ACME — Engineer (2020-2024)\n- Built stuff.\n",
        "jd_text": "Senior Python engineer wanted.",
        "missing_keywords": ["python", "postgres"],
    }
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=_echo_title_mock(),
    ):
        r = await client.post("/api/v1/rewrite/section", json=payload)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["section_id"] == "sec-2"
    assert body["section"]["title"] == "Experience"
    assert body["section"]["content"], "section must come back with content"
    # Contract: only one section returned, no sibling sections.
    assert set(body.keys()) == {"section_id", "section"}
    assert set(body["section"].keys()) >= {"title", "content", "entries"}


async def test_ac4_rewrite_section_validates_required_fields(client):
    """AC-4 — missing required fields return 422, not a silent partial."""
    r = await client.post(
        "/api/v1/rewrite/section",
        json={"section_id": "x"},  # missing title/text/jd
    )
    assert r.status_code == 422


# ─── AC-5: structured 502 error envelope ───────────────────────────────────

async def test_ac5_truncated_response_returns_502_envelope(client):
    """AC-5 — empty LLM response → 502 with {error, message, retry_hint}."""
    def fake_empty(*, task, prompt, **kwargs):
        return ""

    payload = {
        "resume_text": (
            "Jane Doe\njane@example.com\n\n"
            "Summary\nEngineer.\n\n"
            "Experience\nACME — Engineer.\n" + "x" * 100
        ),
        "job_description": "Senior Python engineer wanted. " + "y" * 100,
    }
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_empty,
    ):
        r = await client.post("/api/rewrite", json=payload)

    assert r.status_code == 502, r.text
    body = r.json()
    assert "detail" in body
    envelope = body["detail"]
    assert envelope["error"] == "rewrite_truncated"
    assert envelope["message"]
    assert envelope["retry_hint"] in {"retry", "reduce_input", "contact_support"}


async def test_ac5_malformed_json_returns_502_parse_error(client):
    """AC-5 — malformed JSON → 502 with error=rewrite_parse_error."""
    def fake_bad_json(*, task, prompt, **kwargs):
        return "definitely not JSON {{{{{"

    payload = {
        "resume_text": (
            "Jane Doe\njane@example.com\n\n"
            "Summary\nEngineer.\n\n"
            "Experience\nACME — Engineer.\n" + "x" * 100
        ),
        "job_description": "Senior Python engineer wanted. " + "y" * 100,
    }
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_bad_json,
    ):
        r = await client.post("/api/rewrite", json=payload)

    assert r.status_code == 502, r.text
    envelope = r.json()["detail"]
    assert envelope["error"] == "rewrite_parse_error"


async def test_ac5_section_endpoint_propagates_structured_error(client):
    """AC-5 — the per-section endpoint also returns the structured envelope."""
    def fake_empty(*, task, prompt, **kwargs):
        return ""

    payload = {
        "section_id": "sec-0",
        "section_title": "Experience",
        "section_text": "ACME — Engineer.",
        "jd_text": "Senior Python engineer wanted.",
    }
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_empty,
    ):
        r = await client.post("/api/v1/rewrite/section", json=payload)

    assert r.status_code == 502, r.text
    envelope = r.json()["detail"]
    assert envelope["error"] == "rewrite_truncated"
    assert envelope["retry_hint"]


# ─── Happy path smoke test — AC-1 at route level ───────────────────────────

async def test_route_level_full_rewrite_returns_populated_sections(client):
    """Route-level: a successful rewrite returns populated sections (AC-1/AC-6)."""
    payload = {
        "resume_text": (
            "Jane Doe\njane@example.com | 555-1234\n\n"
            "Summary\nSeasoned engineer with a decade of experience. "
            + "x" * 100 + "\n\n"
            "Experience\nACME — Senior Engineer (2020-2024)\n- Built stuff. "
            + "y" * 100 + "\n\n"
            "Skills\nPython, Go, Rust."
        ),
        "job_description": "Senior Python engineer wanted. " + "z" * 100,
    }
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=_echo_title_mock(),
    ):
        r = await client.post("/api/rewrite", json=payload)

    assert r.status_code == 200, r.text
    body = r.json()
    # LD-5: sections is populated and full_text is retained.
    assert isinstance(body["sections"], list)
    assert len(body["sections"]) >= 4  # Contact + Summary + Experience + Skills
    titles = [s["title"] for s in body["sections"]]
    assert titles[0] == "Contact"
    assert "Summary" in titles
    assert "Experience" in titles
    assert "Skills" in titles
    assert body["full_text"], "full_text retained for copy-to-clipboard (LD-5)"
