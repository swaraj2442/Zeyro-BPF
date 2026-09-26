# Context Handoff — BITSoM Vertex Buildathon (BFSI AI Track)

## Event
BITSoM Vertex AI Incubator "Day-1 Builders Pitch Fest," BFSI track, in
partnership with LENZ. Started 11:00 AM, demo/judging at 5:30 PM (7 min
demo + 3 min Q&A). Team size max 2.

**Hard rules to respect:**
- Synthetic data only — no real confidential/financial/PII data
- Code must be substantially built during the challenge window — no
  pre-existing private/proprietary code (concepts from our own architecture
  are fine to reuse, but not literal pre-written code)
- No hardcoded responses used to fake AI quality — scores/detection must be
  computed dynamically from data every run
- Must state assumptions clearly in the presentation
- One slide + working demo + Q&A; demo code uploaded to the submission link
  at 5:30 PM sharp

## Who's building this
Swaraj Chouriwar, CEO/co-founder of Zeyro (Arthazeyro Technologies), an
AI-native fintech with an existing B2B behavioral credit intelligence
platform (six-agent architecture: Credit Sentinel, Fraud Watchdog,
Collections Oracle, Wellness Advisor, Compliance Guard, Onboarding Bot;
Behavioral Financial Score model, XGBoost, AUC 0.79, trained on Indian
bank/CIBIL data). Team of 2 for this buildathon.

---

## PIVOT: the idea is now "Zeyro Trade Sentinel" — trade finance, not mule/credit

**Superseded:** the original plan combined a generic mule-account "Fraud
Watchdog" demo with a "Credit Sentinel" credit-scoring screen on one shared
behavioral engine. That plan is dropped as the headline story — it's less
differentiated and doesn't fit the GIFT IFSC context. **Credit Sentinel is
dropped from the main story entirely for this buildathon.**

**New framing:** trade finance is inherently a network problem — an
exposure involves an exporter, importer, bank, factor, invoice, shipment,
insurer and multiple payment counterparties. Traditional systems evaluate
these individually (invoice → check). Zeyro Trade Sentinel connects the
relationships instead.

```
Trade Data → Behavioural Graph → Risk Intelligence → Decision

  EXPORTER → INVOICE → IMPORTER
                │           │
                ▼           ▼
            SHIPMENT      BANK
                │           │
                └─────┬─────┘
                      ▼
             TRANSACTION GRAPH
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  Counterparty    Money Flow    Behaviour
  relationships    patterns    over time
        └─────────────┼─────────────┘
                      ▼
         ZEYRO BEHAVIOURAL INTELLIGENCE LAYER
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   TRADE RISK               FRAUD / AML
   INTELLIGENCE             INTELLIGENCE
          └───────────┬───────────┘
                      ▼
          TRADE-FINANCE DECISION
```

### What the engine looks for (5 behavior families — same shape as before, retargeted)
- **Network behaviour** — fan-in/fan-out, counterparty concentration,
  centrality, hidden relationships
- **Money-flow behaviour** — velocity, pass-through activity, unusual
  inflow/outflow, rapid dispersion of funds
- **Temporal behaviour** — dormant → active relationships, sudden volume
  changes, abnormal transaction sequences
- **Entity behaviour** — observed activity vs. declared profile/expected
  business volume/known counterparties
- **Transaction relationships** — repeated cycles, unusual routing,
  interconnected entities across the trade ecosystem

**The concrete, buildable-in-a-day target: duplicate invoice financing
detection.** An exporter submits the same invoice (or a slightly altered
version) to multiple financiers/factors to get financed twice. This is a
real, well-documented, high-value fraud pattern (see precedent below) and
maps directly onto the graph engine already built — same fan-in/fan-out,
pass-through, and cycle-detection features, just relabeled onto trade
entities (Exporter/Invoice/Bank/Factor nodes instead of generic accounts).

### Why this is more differentiated than the mule/credit version
- Fits the GIFT IFSC context directly — IFSCA has a **named regulatory
  framework specifically for this**: the Framework for setting up an
  International Trade Financing Services Platform (ITFS), 2021, alongside
  IFSCA's broader TechFin framework which explicitly covers AI/ML, fraud
  detection/prevention, and risk management. This is a direct regulatory
  home for the product category, not a hypothetical market.
- IFSCA's FinTech Regulatory Sandbox / Innovation Sandbox grants Limited
  Use Authorization with **no requirement** for an office, a deployable
  product, or a revenue track record — frame the buildathon prototype as a
  legitimate first sandbox step, not just a demo.
- Doesn't require convincing judges that one score should serve two
  unrelated purposes (fraud + credit) — it's one coherent story: relationship
  risk in trade finance.

### Citations for the slide / Q&A (trade-finance specific — replaces the mule/credit citation set)

**Regulatory:**
- **IFSCA ITFS Framework, 2021** — GIFT IFSC's dedicated trade-finance
  platform regulation
- **IFSCA TechFin Framework + Regulatory Sandbox** — explicitly covers
  AI/ML, fraud detection, KYC/AML/CFT, risk management; sandbox entry has no
  product/revenue bar

**The real fraud case that motivates the pitch:**
- **2018 Punjab National Bank fraud (~$1.8B)** — unauthorized Letters of
  Undertaking issued outside the core banking system, undetected because
  SWIFT messaging wasn't reconciled against internal bank records. The
  canonical Indian trade-finance fraud scandal — a "relationship/network
  wasn't being watched" failure, exactly the gap this pitch closes. Open
  with this, not with an abstract framing line.

**Production precedent — India-specific, use this as the anchor comp:**
- **MonetaGo** — live in India since 2018, connects all three RBI-licensed
  TReDS exchanges (RXIL, A.TReDS, M1xchange — RXIL is an NSE/SIDBI JV for
  MSME receivables financing). Detects duplicate invoice financing across
  platforms even when the invoice has been altered to look different.
  Cross-validates against India's GSTN database and NIC eWay Bill portal,
  not just its own ledger. Has prevented billions in losses since 2018; also
  selected by the Association of Banks in Singapore for the same purpose
  cross-border. **This is the single best comp — near-exact structural
  precedent for the Exporter→Invoice→Bank→Factor graph**, but it doesn't do
  the deeper counterparty/network behavioral layer Trade Sentinel adds.

**Commercial precedent — global:**
- **Surecomp** — sells "Duplicate Invoice Fraud Prevention" to banks via
  hashed invoice fingerprints shared across a validation network
- **Duality Technologies** — privacy-preserving cross-lender duplicate
  financing checks without exposing sensitive borrower data between banks
- **Coupa SpendGuard** — AI duplicate-invoice/fraud detection at enterprise
  AP level; evidence the underlying technique is mainstream, not novel risk

**Academic:**
- **FlowScope (AAAI)** — published graph algorithm for spotting money
  laundering by tracing flow through a transaction network — maps directly
  onto the Exporter→Invoice→Shipment→Bank→Payment flow diagram
- Systematic literature review of trade-based money laundering (TBML)
  categorizes the field into risk assessment, detection, and the role of
  professionals — supports the "challenge isn't more data, it's connecting
  the data" framing as an established distinction in the literature
- GNN-for-AML research treats **layering** (moving funds through multiple
  entities to obscure origin) as the hardest, most graph-native laundering
  stage — exactly what an exporter→bank→factor→insurer chain represents
  structurally

**One-line synthesis for the slide:** *"IFSCA has already built the
regulatory home for trade-finance platforms at GIFT City. MonetaGo proves
duplicate-financing detection works in production on India's own TReDS
exchanges. We're adding the behavioral-graph layer — counterparty
relationships and flow patterns, not just invoice fingerprints — that
neither currently does."*

### Product framing (from the one-pager)
**Zeyro Trade Sentinel** — a decision-intelligence layer for trade-finance
teams, positioned at 4 points in the workflow:
- **Before approval** — Counterparty Intelligence: "Who is this entity
  connected to?"
- **During processing** — Transaction Intelligence: "Does the observed
  flow behave like the stated trade relationship?"
- **During monitoring** — Behavioural Early Warning: "Has the relationship
  changed in a way that warrants investigation?"
- **When an anomaly appears** — Explainable Investigation: "What changed,
  where did the signal originate, which entities are connected?"

**Differentiation framing:** traditional systems are document-centric or
transaction-centric (Invoice → Check). Zeyro is relationship-centric
(Invoice → Exporter → Importer → Bank → Counterparties → Transaction flows
→ Historical behaviour). Not a replacement for existing AML/KYC/credit/
trade-finance systems — a behavioural intelligence layer on top of them.

**Land → Expand (for the "what's next" close):** Trade/counterparty risk
intelligence → Fraud & AML monitoring → Portfolio early-warning →
Behavioural intelligence across institutional financial decisions.

---

## What's already built and tested (working, from the earlier mule/credit
plan — reusable, just relabel the entities)

Scaffold lives at `/mnt/user-data/outputs/mulehunter-scaffold/` — 5 files,
all smoke-tested end to end (365 synthetic accounts, 1943 transactions,
live API confirmed). **The graph engine itself doesn't need to be rebuilt
— it needs to be relabeled and re-scenario'd for trade entities.**

1. **`data_gen.py`** — synthetic account + transaction generator, currently
   modeling generic "accounts." **To adapt for Trade Sentinel:** rename/
   extend the entity model to Exporter / Importer / Bank / Factor / Invoice
   nodes, and make the primary injected pattern **duplicate invoice
   financing** (same invoice — or a near-duplicate with altered
   amount/reference — submitted to two different financier nodes) as the
   headline demo case, alongside the existing 5 pattern families reframed:
   - fan-in/fan-out → **many invoices/factors converging on one entity**
   - dormant-then-active → **a quiet counterparty relationship suddenly
     highly active**
   - round-tripping → **circular invoicing/payment between related entities**
   - velocity spike → **abnormal transaction sequence / rapid volume change**
   - KYC/volume mismatch → **observed activity vs. declared business
     profile/expected volume**

2. **`scoring.py`** — the Behavioral Risk Engine. Builds a NetworkX
   MultiDiGraph, computes 8 features per node (pagerank_shift, betweenness,
   fan_ratio, pass_through_ratio, velocity, kyc_volume_mismatch,
   dormancy_burst, short_cycle), combines via `RISK_WEIGHTS` into a 0-100
   score with per-node evidence. No hardcoded verdicts — computed from data
   each run. **Add one new explicit feature: `duplicate_invoice_match`** —
   fuzzy-match invoice reference/amount/counterparty across financier nodes
   (this is the single most demo-able, judge-legible signal, and it's
   exactly what MonetaGo does in production, so it's a safe, well-precedented
   feature to add).

3. **`api.py`** — FastAPI service. Endpoints unchanged in shape:
   - `GET /accounts` (rename conceptually to `/entities` if time allows,
     or keep as-is and just relabel in the frontend)
   - `GET /accounts/{id}` — full evidence — feeds the agent prompt
   - `GET /graph` — nodes/edges for the graph viz
   - `POST /regenerate`, `GET /health`

4. **`requirements.txt`** — fastapi, uvicorn, networkx

5. **`README.md`** — setup instructions + the open tuning task (still
   applies: separation between normal and flagged entities needs live
   tuning — this is real judged work, not a defect, per Flagright's 83%
   false-positive-reduction positioning and why RBIH built MuleHunter.AI in
   the first place)

### Known open issue — still applies, now with a trade-finance framing
Pattern separation isn't clean out of the box; some normal entities
incidentally trigger `short_cycle` from random graph structure. **Now that
duplicate invoice matching is the headline demo**, prioritize getting that
one feature crisp and well-separated over polishing the other four — it's
the single feature judges will immediately recognize as "the MonetaGo
problem, plus relationship context."

### Environment note (learned the hard way)
Background processes (`uvicorn ... &`) do NOT persist across separate tool
calls in a sandboxed environment — start the server and test it within the
same command/call. Files on disk DO persist across calls. Not an issue in
Claude Code's persistent terminal.

## Roles
- **Person A — Data & Engine**: `data_gen.py`, `scoring.py`, `api.py`,
  duplicate-invoice-match feature, threshold tuning
- **Person B — Experience & Narrative**: frontend (graph viz + the 4-point
  workflow screens — Counterparty Intelligence / Transaction Intelligence /
  Behavioural Early Warning / Explainable Investigation), the agent prompt,
  the one slide, demo rehearsal

## Timeline (11:00 AM start → 5:30 PM demo) — adjust content, keep the shape
| Time | Person A | Person B |
|---|---|---|
| 11:00–11:20 | Together: lock the Trade Sentinel framing, assumptions, architecture sketch | same |
| 11:20–12:30 | Relabel `data_gen.py` entities to trade nodes; build the duplicate-invoice injection pattern | Frontend shell + graph viz wireframe |
| 12:30–14:00 | Add `duplicate_invoice_match` feature to `scoring.py`; re-run pattern-separation check | Write the single agent prompt (Trade Sentinel investigation/explanation note per the 4-point workflow) |
| 14:00–14:15 | Integration checkpoint | |
| 14:15–15:30 | **Tune thresholds — prioritize duplicate-invoice separation** | Wire frontend to live API, graph rendering, live agent call |
| 15:30–16:15 | Support integration, add 1-2 hard demo cases (a clean duplicate-invoice pair + one relationship-based flag) | Polish the 4-screen workflow view |
| 16:15–16:45 | Together: end-to-end run-through, freeze build | |
| 16:45–17:00 | | Build the one slide (PNB fraud framing, architecture diagram, 3 citations — IFSCA ITFS, MonetaGo, FlowScope — assumptions, land→expand) |
| 17:00–17:30 | Together: rehearse demo twice, upload code | |

## Demo script (7 min + 3 min Q&A) — updated
1. **0:00–1:00** — Open with the PNB/Nirav Modi fraud as the real-world
   stakes. Frame: trade finance is a network problem, not a document
   problem.
2. **1:00–4:00** — Live: show the graph, click a flagged entity pair with a
   duplicate invoice match, show the agent's explanation (which
   counterparties, which invoice, why it's flagged).
3. **4:00–6:00** — Show one relationship-based flag (e.g. a dormant
   counterparty suddenly active, or a short cycle) to demonstrate the
   engine goes beyond simple invoice-fingerprint matching (the MonetaGo
   layer) into full behavioral-graph territory.
4. **6:00–7:00** — Architecture slide, citations, stated assumptions,
   land→expand close.

## What's still needed next (not yet built)
1. Relabel/extend `data_gen.py` for trade entities + duplicate-invoice
   pattern
2. Add `duplicate_invoice_match` feature to `scoring.py`
3. One agent prompt (Trade Sentinel), consuming `GET /accounts/{id}`
   evidence, structured around the 4-point workflow (counterparty /
   transaction / early-warning / investigation framing)
4. Frontend: graph viz + relabeled entity types, single flagged-pair demo
   view
5. The one slide: PNB fraud opening, architecture diagram, 3 citations
   (IFSCA ITFS, MonetaGo, FlowScope), assumptions, land→expand
6. Demo rehearsal against the updated script above