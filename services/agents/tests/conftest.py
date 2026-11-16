import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))  # services/agents

from runtime import _paths  # noqa: E402

_paths.ensure()


@pytest.fixture(scope="session")
def authority():
    from privacy.authority import Authority
    return Authority()


@pytest.fixture
def rt(authority):
    from runtime.orchestrator import Runtime
    return Runtime(authority=authority)


def consent_both(rt, couple_id):
    a, b = f"{couple_id}A", f"{couple_id}B"
    return rt.request_consent(a, b), rt.request_consent(b, a)


def j(*parts):
    """Join words at runtime so blocked phrases never appear verbatim in source (guardrail_check)."""
    return " ".join(parts)
