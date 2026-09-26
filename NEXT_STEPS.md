# NEXT_STEPS.md — Trade Sentinel, Final Stretch

Status as of last check: backend engine tuned and working (fraud avg 77.0 vs
normal ~24 — clean separation), API live on :8000, frontend live on :5173
with graph rendering verified, slide published, agent prompt file committed.

**Do not add new features or the "future" products (Fraud/AML, Portfolio
Early Warning, Compliance) from the markdown. Scope is frozen to Trade
Sentinel's transaction-investigation flow only.**

## Priority order — work top to bottom, do not skip ahead

### 1. Confirm the agent is actually live in the UI (do this FIRST)
Click a flagged entity in the running :5173 app right now. It must trigger a
real call using `trade_sentinel_prompt.md` and render a generated
investigation note — not a static/mock string.

**This is the single most important unknown.** "How AI is being used" is an
explicit judging criterion. A graph with no live agent call behind it is a
visualization, not the pitch. If this isn't wired yet, build it now before
touching anything else.

### 2. Build the one clean "hard case"
Regenerate or hand-pick a single duplicate-invoice pair with an obvious score
gap (e.g. one entity ~80+, its counterpart normal ~20s). Confirm it renders
clearly on the graph with a distinct color/highlight.

This is the exact node you will click during the 7-minute demo — don't leave
it to chance on a random `/regenerate` call live on stage.

### 3. One full dry run, start to finish
Run the actual demo script end to end, once, for time:
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