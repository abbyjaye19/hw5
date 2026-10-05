"""Reset the working DB: copy the original data/campus_customs.db over data/campus_customs_new.db.

Run before every full ticket-resolution run:  python -m backend.reset_db
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from backend.config import HW_ROOT

ORIGINAL = HW_ROOT / "data" / "campus_customs.db"
WORKING = Path(os.getenv("CAMPUS_CUSTOMS_DB", HW_ROOT / "data" / "campus_customs_new.db"))


def reset_working_db() -> None:
    if WORKING.resolve() == ORIGINAL.resolve():
        raise RuntimeError("Working DB path points at the original; refusing to reset.")
    shutil.copyfile(ORIGINAL, WORKING)
    print(f"Reset {WORKING.name} from {ORIGINAL.name}")


if __name__ == "__main__":
    reset_working_db()
