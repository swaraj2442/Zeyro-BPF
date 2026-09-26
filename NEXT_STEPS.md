# NEXT_STEPS.md — Trade Sentinel, Final Stretch

**Status: 2 of 6 priorities COMPLETE ✓**

- ✓ **#1 Agent live in UI** — POST /investigate/{entity_id} wired to Groq (openai/gpt-oss-120b), calls trade_sentinel_prompt.md with live evidence, dynamically renders markdown notes. Caching + debouncing prevent rate limits. Falls back to local computed note if Groq fails (demo never goes blank).
- ✓ **#2 Hard case locked** — Seed 107: FRAUD_0000 @ 77.8/100 (32-point separation vs max normal 45.7), duplicate-invoice-financing pattern, guaranteed on startup.

**Working state:** API on :8000, frontend on :5173 (auto-selects FRAUD_0000 with live agent note), slide published, all code committed.

**Do not add new features or the "future" products (Fraud/AML, Portfolio
Early Warning, Compliance) from the markdown. Scope is frozen to Trade
Sentinel's transaction-investigation flow only.**

## Priority order — work top to bottom, do not skip ahead

### 1. ✓ DONE: Confirm agent is live in the UI
**COMPLETED** — Live Groq calls verified working, caching prevents rate limits, markdown rendering clean, fallback ready.

### 2. ✓ DONE: Build the one clean "hard case"
**COMPLETED** — Seed 107 hand-picked via exhaustive search, FRAUD_0000 guaranteed @ 77.8/100 with duplicate-invoice evidence. Graph renders with FRAUD_0000 auto-selected on every load (red dot, high-risk indicator). No randomness on stage.

### 3. One full dry run, start to finish (DO THIS NOW)
Run the actual demo script end to end, once, for time, TODAY (before 5:30pm upload):
- Open the slide
- Switch to the browser
- Click the hard case
- Read the agent's investigation note aloud
- Close on the slide's land→expand section

Time it. If it runs over 7 minutes, cut narration, not screens.

### 4. Freeze the build
Once the dry run works, **stop touching `scoring.py` and `data_gen.py`.** A
last-minute threshold tweak that breaks the hard case ten minutes before
judging is the most common way teams lose a working demo.

### 5. Rehearse the Q&A, not just the demo
Assign who answers what:
- **Assumptions**: synthetic data, ≥75% invoice-match threshold, stated score
  thresholds
- **"Why not blockchain?"**: we.trade / Marco Polo Network / TradeLens
  (IBM, Mastercard, 40+ banks combined) all failed because they required
  consortium-wide infrastructure adoption; MonetaGo succeeded as a
  lightweight overlay on existing systems since 2018 — Trade Sentinel follows
  MonetaGo's model, not the consortium model
- **Land → expand roadmap**: Trade/counterparty risk → Fraud & AML → Portfolio
  early-warning → Platform

A confident 3-minute Q&A matters as much as the 7-minute demo.

### 6. Upload code at 5:30pm
Confirm everything except `venv`/`node_modules` (gitignored, regenerable via
`uv pip install` and `npm install`) is committed. Push and upload to the
submission link with time to spare — not at 5:29.

## If time runs short, cut in this order
1. Cut extra narration in the dry run before cutting any screen
2. Skip polishing a second/backup hard case — one clean flagged pair is enough
3. Never cut: step 1 (agent live in UI), step 4 (freeze), step 6 (upload)