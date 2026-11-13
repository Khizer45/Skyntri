"""
Optional in-process scheduler for the built-in agents.

Enabled with AGENTS_SCHEDULER_ENABLED=true. Every minute it checks which
agent runs are due. A unique run key per period makes each run happen
once, even with several server processes.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from app.core.config import settings
from app.db.database import SessionLocal
from app.services import agents
from app.services.clinic import clinic_tz

logger = logging.getLogger("skyntri.scheduler")

_stop = threading.Event()
_thread: threading.Thread | None = None


def tick(session_factory=SessionLocal, now_local: datetime | None = None) -> list[str]:
    """Run whatever is due. Returns the run keys that were executed now."""
    executed = []
    now_local = now_local or datetime.now(clinic_tz())
    for name, run_key in agents.due_runs(now_local):
        with session_factory() as db:
            if agents.run_agent(db, name, "schedule", run_key) is not None:
                executed.append(run_key)
    return executed


def _loop() -> None:
    while not _stop.wait(60):
        try:
            tick()
        except Exception:
            logger.exception("scheduler_tick_failed", extra={"event": "scheduler_tick_failed"})


def start() -> None:
    global _thread
    if not settings.agents_scheduler_enabled or _thread is not None:
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="skyntri-agents", daemon=True)
    _thread.start()
    logger.info("scheduler_started", extra={"event": "scheduler_started"})


def stop() -> None:
    global _thread
    _stop.set()
    _thread = None
