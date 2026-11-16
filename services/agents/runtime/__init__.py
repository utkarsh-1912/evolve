"""runtime - the seven runtime agents, the BioethicsSupervisor gate and orchestration (R-AGT-1/2/3).

Named `runtime` (not `agents`) so the repo-root `agents/` briefs folder cannot shadow it (contracts/api.md).
`runtime.bioethics` is stdlib-only and importable on its own (qa-redteam tests against it).
Heavier modules (orchestrator, agents) import risk_engine/privacy lazily via `runtime._paths`.
"""

__all__ = ["bioethics", "run_compatibility"]


def run_compatibility(couple_id: str, runtime=None) -> dict:
    from .orchestrator import run_compatibility as _run

    return _run(couple_id, runtime)
