# HW5: Campus Customs Multi-Agent Operations

MCP server (`mcp_server/`) + FastAPI multi-agent backend + React dashboard. Agents: Boss, Inventory, Accounting, Facilities, Customer Service. Any agent may delegate to any other.

## Rules for working in this repo

- **Prompt log:** after every prompt the user types, update `AI_prompts.md`: one section per problem (number + title), the prompt in the user's own words but cleaned up for spelling, grammar and clarity (first person, same meaning; rewording is fine), and any follow-up prompt with one sentence on what was lacking after the first. Apply the same cleanup to any other "in my own words" text (e.g. in `output/desk_tickets.html`).
- **Model:** every agent uses ONLY `gpt-6-luna` through Portkey (`PORTKEY_API_KEY` in `.env` here or in a parent folder). No other model name may appear in code or runs.
- **Databases:** `data/campus_customs.db` is the original. Never modify it. All tools and the backend use `data/campus_customs_new.db`. Reset the working copy from the original before any full ticket-resolution run.
- **Business rules:** "today" = `desk.date_today`. Vendor lead times come from `vendors.lead_days`. A vendor with an open unpaid invoice won't ship. Every payment needs human approval and must update the related tables. The pay tool refuses if cash would go negative. Cash only goes out. Never email customers or contact vendors; drafts stay on the board.
- **Harness:** `output/harness.md` grows with each problem.
- **Python:** use `.venv/Scripts/python.exe` (deps in `requirements.txt`).
