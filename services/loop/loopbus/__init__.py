"""loopbus - closed-loop care state machine + SIMULATED adapters (R-UX-3 backend, docs/02 §6)."""
from .adapters import SIMULATED, SimulatedAdapter, default_adapters  # noqa: F401
from .machine import (  # noqa: F401
    BOOKING_WINDOW,
    HUMAN_ONLY,
    STATES,
    ForbiddenTransition,
    LoopBus,
    LoopError,
    SimulatedClock,
)
