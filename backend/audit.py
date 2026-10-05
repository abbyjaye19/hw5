"""Append-only audit trail at output/audit_trail.json (a JSON array that is never wiped)."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_core import to_jsonable_python

from backend.config import AUDIT_PATH
from backend.models import AgentDeps, AuditEntry

MAX_TEXT = 4000  # clip very long strings so the trail stays readable


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"... [+{len(value) - MAX_TEXT} chars]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value]
    return value


class AuditTrail:
    def __init__(self, path: Path = AUDIT_PATH):
        self.path = path
        self._lock = asyncio.Lock()
        self.listeners: list[Any] = []  # callables(entry_dict) for live streaming later

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            # Never lose history: keep the unreadable file aside and start a fresh array.
            backup = self.path.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json")
            self.path.replace(backup)
            return []

    async def record(
        self, deps: AgentDeps, event: str, step_no: int | None = None, **details: Any
    ) -> dict[str, Any]:
        entry = AuditEntry(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            run_id=deps.team.run_id,
            ticket_id=deps.team.ticket_id,
            agent=deps.agent,
            depth=deps.depth,
            chain=list(deps.chain),
            event=event,
            step_no=step_no,
            details=_clip(to_jsonable_python(details, fallback=str)),
        ).model_dump()
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            entries = self._read()
            entries.append(entry)
            payload = json.dumps(entries, indent=2, ensure_ascii=False)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(payload, encoding="utf-8")
            # OneDrive / antivirus can briefly lock the file on Windows; retry, then fall back to a direct write.
            for attempt in range(8):
                try:
                    os.replace(tmp, self.path)
                    break
                except PermissionError:
                    await asyncio.sleep(0.1 * (attempt + 1))
            else:
                self.path.write_text(payload, encoding="utf-8")
                tmp.unlink(missing_ok=True)
        for listener in self.listeners:
            listener(entry)
        return entry
