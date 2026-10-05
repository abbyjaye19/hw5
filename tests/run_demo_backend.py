"""Start the backend in scripted-demo mode on scratch copies (UI testing only, no LLM).

    python tests/run_demo_backend.py

Uses tests/.demo/ for the DB and audit trail, so data/campus_customs_new.db and
output/audit_trail.json are never touched.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
DEMO = HW / "tests" / ".demo"
DEMO.mkdir(exist_ok=True)
shutil.copyfile(HW / "data" / "campus_customs.db", DEMO / "demo.db")
(DEMO / "audit_demo.json").write_text("[]", encoding="utf-8")

os.environ.update(
    CAMPUS_SCRIPTED_DEMO="1",
    CAMPUS_CUSTOMS_DB=str(DEMO / "demo.db"),
    CAMPUS_AUDIT_PATH=str(DEMO / "audit_demo.json"),
)
sys.path.insert(0, str(HW))
sys.path.insert(0, str(HW / "backend"))

import uvicorn  # noqa: E402

uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
