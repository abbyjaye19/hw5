"""CLI: run the agent team on one or more tickets.

    python -m backend.run_ticket 101            # one ticket
    python -m backend.run_ticket --all --reset  # reset the working DB, then every open ticket
"""

from __future__ import annotations

import argparse
import asyncio
import json

from backend.agents.team import CampusTeam
from backend.reset_db import reset_working_db


async def main(ticket_ids: list[int], run_all: bool) -> None:
    async with CampusTeam() as team:
        if run_all:
            open_tickets = await team.mcp.direct_call_tool("list_open_tickets", {})
            ticket_ids = [t["id"] for t in open_tickets]
        for tid in ticket_ids:
            outcome = await team.run_ticket(tid)
            print(json.dumps(outcome.model_dump(), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tickets", nargs="*", type=int)
    parser.add_argument("--all", action="store_true", help="work every open ticket")
    parser.add_argument("--reset", action="store_true", help="reset the working DB from the original first")
    args = parser.parse_args()
    if args.reset:
        reset_working_db()
    asyncio.run(main(args.tickets, args.all))
