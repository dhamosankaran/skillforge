"""Migration roundtrip test for the E-052 / B-125a alembic revision.

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §7.

Marked ``integration`` — runs alembic against the live test DB. CI's
``-m "not integration"`` selector deselects it.
"""
import subprocess
from pathlib import Path

import pytest


REVISION = "e052b125a4f1"


@pytest.mark.integration
def test_migration_roundtrip_e052_user_career_intents():
    """Upgrade head → downgrade -1 → upgrade head must succeed cleanly."""
    backend_dir = Path(__file__).resolve().parent.parent

    def _alembic(*args: str) -> None:
        result = subprocess.run(
            ["alembic", *args],
            cwd=backend_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"alembic {' '.join(args)} failed:\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    _alembic("upgrade", "head")
    _alembic("downgrade", "-1")
    _alembic("upgrade", "head")

    # Confirm we ended at the expected head.
    result = subprocess.run(
        ["alembic", "current"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    assert REVISION in result.stdout
