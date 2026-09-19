from __future__ import annotations

import logging
import os
import sys
import threading
import time

log = logging.getLogger("WORKER")


def start_background() -> None:
    if os.environ.get("DISABLE_WORKERS") == "1" or "pytest" in sys.modules:
        return
    t = threading.Thread(target=_loop, name="lumina-giveaways", daemon=True)
    t.start()


def _loop() -> None:
    from app.db.session import SessionLocal
    from app.services.giveaways import tick

    while True:
        time.sleep(25)
        db = SessionLocal()
        try:
            tick(db)
        except Exception:
            log.exception("giveaway tick")
        finally:
            db.close()
