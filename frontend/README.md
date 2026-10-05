# Campus Customs Operations Desk (frontend)

React + Vite + TypeScript dashboard for the Campus Customs multi-agent team. It talks to the FastAPI backend at **http://localhost:8000** (`src/api.ts`).

```bash
npm install
npm run dev      # opens http://localhost:5173
```

Start the backend first (from `../backend`): `uvicorn main:app --reload --port 8000`.

| File | What it is |
|---|---|
| `src/App.tsx` | State, polling, and wiring between the panels |
| `src/components/Docket.tsx` | Ticket folders with open / in-session / resolved seals |
| `src/components/Boardroom.tsx` | Oval table with agent nameplates and gold delegation lines |
| `src/components/Minutes.tsx` | Live proceedings: what each agent said and which tools it used |
| `src/components/Summary.tsx` | Boss's resolution, per-agent briefs, draft letters |
| `src/components/Treasury.tsx` | Balance, cash-flow ledger, cheques to sign and approve |
| `src/agents.ts` | Agent metadata and folding events into per-agent activity |

Design rationale: see `../output/design.md`.
