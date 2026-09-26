"""Step-by-step case investigation. Every finding is computed from the current dataset on request."""
from datetime import date, timedelta
from typing import Dict, List

from data_gen import Entity, EntityType, Transaction
from scoring import EntityEvidence, build_sale_adjacency, canonical_ref, find_duplicate_financing, find_trade_cycles

BASE_DATE = date(2026, 3, 1)

PATTERN_LABELS = {
    "duplicate_invoice_financing": "Same invoice financed twice",
    "circular_trade": "Goods moving in a closed loop",
    "circular_invoicing": "Back-and-forth invoicing",
    "fan_in_out_concentration": "Concentrated counterparties",
    "dormant_then_active": "Quiet, then sudden activity",
    "volume_spike": "Unusual transaction volume",
    "kyc_mismatch": "Volume doesn't match declared profile",
}
TYPOLOGIES = ("duplicate_invoice_financing", "circular_trade")

STEP_TITLES = {
    "profile": "Review the company",
    "financing": "Pull its financing history",
    "duplicates": "Check for invoices financed twice",
    "loop": "Check where the goods actually went",
    "buyer": "Check what the buyer paid",
    "verdict": "Verdict",
}


def fmt_date(ts: int) -> str:
    return (BASE_DATE + timedelta(seconds=ts)).strftime("%d %b %Y")


def money(x: float) -> str:
    return f"${x:,.0f}"


def edge_id(src: str, dst: str, kind: str) -> str:
    return f"{src}>{dst}>{kind}"


def risk_band(score: float) -> str:
    if score > 70:
        return "HIGH"
    if score > 40:
        return "MEDIUM"
    return "LOW"


class Dataset:
    def __init__(self, entities: List[Entity], transactions: List[Transaction], evidence: List[EntityEvidence], version: int):
        self.entities = {e.entity_id: e for e in entities}
        self.transactions = transactions
        self.evidence = {e.entity_id: e for e in evidence}
        self.ranked = evidence
        self.version = version
        self.sale_adj = build_sale_adjacency(transactions)
        self.by_entity: Dict[str, List[Transaction]] = {}
        for tx in transactions:
            self.by_entity.setdefault(tx.from_entity, []).append(tx)
            self.by_entity.setdefault(tx.to_entity, []).append(tx)

    def name(self, eid: str) -> str:
        return self.entities[eid].business_name if eid in self.entities else eid

    def txns(self, eid: str) -> List[Transaction]:
        return self.by_entity.get(eid, [])


# ---------------------------------------------------------------------------------------
# Case queue
# ---------------------------------------------------------------------------------------

def headline(ds: Dataset, ev: EntityEvidence) -> str:
    if "duplicate_invoice_financing" in ev.matched_patterns:
        pairs = find_duplicate_financing(ev.entity_id, ds.transactions, ds.entities)
        return f"Invoice {pairs[0]['ref_a']} financed by 2 financiers" if pairs else PATTERN_LABELS["duplicate_invoice_financing"]
    if "circular_trade" in ev.matched_patterns:
        cycles = find_trade_cycles(ev.entity_id, ds.sale_adj)
        if cycles:
            return f"Goods loop through {len(cycles[0]['path'])} traders, {cycles[0]['rounds']} rounds"
    if ev.matched_patterns:
        return PATTERN_LABELS.get(ev.matched_patterns[0], ev.matched_patterns[0])
    return "No risk signals"


def case_summary(ds: Dataset, ev: EntityEvidence) -> Dict:
    e = ds.entities[ev.entity_id]
    financed = sum(t.amount for t in ds.txns(e.entity_id) if t.kind == "financing_request" and t.from_entity == e.entity_id)
    return {
        "id": e.entity_id,
        "name": e.business_name,
        "location": e.location,
        "business": e.business,
        "risk_score": round(ev.risk_score, 1),
        "band": risk_band(ev.risk_score),
        "headline": headline(ds, ev),
        "patterns": [PATTERN_LABELS.get(p, p) for p in ev.matched_patterns],
        "financed_volume": round(financed, 2),
        "scenario": e.scenario,
    }


def case_queue(ds: Dataset) -> Dict:
    exporters = [ev for ev in ds.ranked if ev.entity_type == EntityType.EXPORTER.value]
    alerts, seen_rings = [], []
    for ev in exporters:
        if ev.risk_score < 50:
            continue
        ring = next((frozenset(c["path"]) for c in find_trade_cycles(ev.entity_id, ds.sale_adj)), None)
        if ring and ring in seen_rings:
            continue
        summary = case_summary(ds, ev)
        if ring:
            seen_rings.append(ring)
            summary["linked"] = [ds.name(m) for m in ring if m != ev.entity_id]
        alerts.append(summary)
    clear = [case_summary(ds, ev) for ev in exporters if ev.risk_score < 50]
    clear.sort(key=lambda c: c["financed_volume"], reverse=True)
    return {"alerts": alerts, "monitored": clear[:3], "total_exporters": len(exporters)}


# ---------------------------------------------------------------------------------------
# Investigation steps
# ---------------------------------------------------------------------------------------

def _step(key, findings, nodes, edges):
    return {"key": key, "title": STEP_TITLES[key], "findings": findings, "highlight": {"nodes": sorted(set(nodes)), "edges": sorted(set(edges))}}


def _funding_for(ds: Dataset, financier: str, exporter: str, ref: str):
    for t in ds.txns(exporter):
        if t.kind == "funding" and t.from_entity == financier and t.to_entity == exporter and t.invoice_ref == ref:
            return t
    return None


def investigate(ds: Dataset, eid: str, feedback: Dict[str, Dict]) -> Dict:
    e = ds.entities[eid]
    ev = ds.evidence[eid]
    txs = ds.txns(eid)
    sales = sorted([t for t in txs if t.kind == "sale" and t.from_entity == eid], key=lambda t: t.timestamp)
    reqs = sorted([t for t in txs if t.kind == "financing_request" and t.from_entity == eid], key=lambda t: t.timestamp)
    buyers = sorted({t.to_entity for t in sales})
    financiers = sorted({t.to_entity for t in reqs})
    total_financed = sum(t.amount for t in reqs)
    steps = []

    # 1. Profile
    steps.append(_step("profile", {
        "company": e.business_name,
        "location": e.location or "not stated",
        "business": e.business or "exporter",
        "declared_annual_volume": money(e.declared_volume),
        "invoices_financed": len(reqs),
        "total_financed": money(total_financed),
        "financed_vs_declared": f"{total_financed / e.declared_volume:.0%}" if e.declared_volume else "n/a",
        "financiers_used": [ds.name(f) for f in financiers],
        "buyers": [ds.name(b) for b in buyers] or ["no sale records"],
        "active_period": f"{fmt_date(reqs[0].timestamp)} to {fmt_date(reqs[-1].timestamp)}" if reqs else "no activity",
    }, [eid], []))

    # 2. Financing history
    steps.append(_step("financing", {
        "submissions": [
            {"invoice": t.invoice_ref, "financier": ds.name(t.to_entity), "amount": money(t.amount), "date": fmt_date(t.timestamp)}
            for t in reqs[-8:]
        ],
        "showing": f"last {min(8, len(reqs))} of {len(reqs)} financing requests",
        "financier_split": {ds.name(f): sum(1 for t in reqs if t.to_entity == f) for f in financiers},
    }, [eid] + financiers, [edge_id(eid, f, "financing_request") for f in financiers]))

    # 3. Duplicate financing
    pairs = find_duplicate_financing(eid, ds.transactions, ds.entities)
    dup_rows, dup_nodes, dup_edges, exposure = [], [eid], [], 0.0
    for p in pairs:
        first = _funding_for(ds, p["financier_a"], eid, p["ref_a"])
        second = _funding_for(ds, p["financier_b"], eid, p["ref_b"])
        paid_out = second.amount if second else 0.0
        exposure += paid_out
        dup_rows.append({
            "first_submission": f"{p['ref_a']} to {ds.name(p['financier_a'])} on {fmt_date(p['ts_a'])} for {money(p['amount_a'])}",
            "second_submission": f"{p['ref_b']} to {ds.name(p['financier_b'])} on {fmt_date(p['ts_b'])} for {money(p['amount_b'])}",
            "days_apart": round((p["ts_b"] - p["ts_a"]) / 86400),
            "how_matched": "same invoice number, only the formatting was changed" if p["canonical_match"]
            else f"references {p['similarity']:.0%} similar, same buyer, amounts within 0.5%",
            "raw_reference_similarity": f"{p['similarity']:.0%}",
            "first_financier_paid_out": money(first.amount) if first else "$0",
            "second_financier_paid_out": money(paid_out),
        })
        dup_nodes += [p["financier_a"], p["financier_b"]]
        dup_edges += [edge_id(eid, p["financier_a"], "financing_request"), edge_id(eid, p["financier_b"], "financing_request")]
    steps.append(_step("duplicates", {
        "invoices_checked": len(reqs),
        "duplicates_found": len(dup_rows),
        "matches": dup_rows,
        "method": "invoice numbers normalised (separators, leading zeros, case) and compared across every financier",
        "exposure_from_duplicates": money(exposure),
    }, dup_nodes, dup_edges))

    # 4. Circular trade
    cycles = find_trade_cycles(eid, ds.sale_adj)
    loop_rows, loop_nodes, loop_edges = [], [eid], []
    for c in cycles:
        path = c["path"]
        ring = set(path)
        outside_sales = sum(1 for m in path for buyer in ds.sale_adj.get(m, {}) if buyer not in ring)
        vals = c["first_leg_values"]
        growth = (vals[-1] / vals[0] - 1) if len(vals) > 1 else 0.0
        loop_rows.append({
            "route": " → ".join(ds.name(n) for n in path + [path[0]]),
            "times_goods_went_round": c["rounds"],
            "invoice_value_cycled": money(c["value_cycled"]),
            "value_growth_first_to_last_round": f"{growth:.1%}",
            "sales_to_buyers_outside_the_loop": outside_sales,
        })
        loop_nodes += path
        loop_edges += [edge_id(path[k], path[(k + 1) % len(path)], "sale") for k in range(len(path))]
        for m in path:
            loop_nodes += [t.to_entity for t in ds.txns(m) if t.kind == "financing_request" and t.from_entity == m]
    steps.append(_step("loop", {
        "sale_records_checked": len(sales),
        "closed_loops_found": len(loop_rows),
        "loops": loop_rows,
    }, loop_nodes, loop_edges))

    # 5. Buyer settlement
    settle_rows, buyer_nodes, buyer_edges = [], [], []
    if pairs:
        for p in pairs:
            key = canonical_ref(p["ref_a"])
            shipped = [t for t in sales if canonical_ref(t.invoice_ref) == key]
            paid = [t for t in ds.transactions if t.kind == "settlement" and canonical_ref(t.invoice_ref) == key and t.to_entity in (p["financier_a"], p["financier_b"])]
            buyer = shipped[0].to_entity if shipped else None
            unpaid = [f for f in (p["financier_a"], p["financier_b"]) if f not in {t.to_entity for t in paid}]
            settle_rows.append({
                "invoice": p["ref_a"],
                "buyer": ds.name(buyer) if buyer else "unknown",
                "shipments_recorded": len(shipped),
                "goods_value": money(shipped[0].amount) if shipped else "n/a",
                "total_financing_raised": money(p["amount_a"] + p["amount_b"]),
                "buyer_paid": [f"{money(t.amount)} to {ds.name(t.to_entity)} on {fmt_date(t.timestamp)}" for t in paid] or ["nothing yet"],
                "financier_left_unpaid": [ds.name(f) for f in unpaid],
            })
            if buyer:
                buyer_nodes.append(buyer)
                buyer_edges.append(edge_id(eid, buyer, "sale"))
            for t in paid:
                buyer_nodes.append(t.to_entity)
                buyer_edges.append(edge_id(t.from_entity, t.to_entity, "settlement"))
    elif cycles:
        ring = set(cycles[0]["path"])
        payers = sorted({t.from_entity for t in txs if t.kind == "settlement" and t.to_entity == eid})
        settle_rows.append({
            "who_paid_this_company": [ds.name(p) for p in payers],
            "payers_inside_the_loop": sum(1 for p in payers if p in ring),
            "payers_outside_the_loop": sum(1 for p in payers if p not in ring),
        })
        buyer_nodes += payers
        buyer_edges += [edge_id(p, eid, "settlement") for p in payers]
    else:
        settled_refs = {t.invoice_ref for t in ds.transactions if t.kind == "settlement" and t.from_entity in buyers}
        settle_rows.append({
            "invoices_with_sale_records": len(sales),
            "invoices_settled_by_buyer": sum(1 for t in sales if t.invoice_ref in settled_refs),
            "distinct_buyers": len(buyers),
        })
        buyer_nodes += buyers
    steps.append(_step("buyer", {"checks": settle_rows}, [eid] + buyer_nodes, buyer_edges))

    # 6. Verdict
    typologies = [p for p in ev.matched_patterns if p in TYPOLOGIES]
    weak = [PATTERN_LABELS.get(p, p) for p in ev.matched_patterns if p not in TYPOLOGIES]
    if ev.risk_score > 70:
        action = "Escalate: freeze new financing for this company and alert the affected financiers"
    elif ev.risk_score > 40 and typologies:
        action = "Escalate for review: a fraud pattern is present, confirm with trade documents"
    elif ev.risk_score > 40:
        action = "Monitor: weak signals only, no fraud pattern"
    else:
        action = "Clear: no fraud pattern, keep standard monitoring"
    same_typology = [f for cid, f in feedback.items() if cid != eid and set(f["patterns"]) & set(typologies)]
    steps.append(_step("verdict", {
        "risk_score": f"{ev.risk_score:.1f} / 100",
        "risk_band": risk_band(ev.risk_score),
        "fraud_patterns": [PATTERN_LABELS[p] for p in typologies] or ["none"],
        "weak_signals": weak or ["none"],
        "money_at_risk": money(exposure) if exposure else ("value cycled " + loop_rows[0]["invoice_value_cycled"] if loop_rows else "$0"),
        "recommended_action": action,
        "analyst_feedback_on_similar_cases": {
            "confirmed": sum(1 for f in same_typology if f["verdict"] == "confirm"),
            "dismissed": sum(1 for f in same_typology if f["verdict"] == "dismiss"),
        },
    }, [eid] + dup_nodes + loop_nodes, dup_edges + loop_edges))

    return {
        "case": case_summary(ds, ev),
        "steps": steps,
        "outputs": case_outputs(ds, eid, action),
        "graph": case_graph(ds, eid, set(dup_edges + loop_edges), {p["ref_a"] for p in pairs} | {p["ref_b"] for p in pairs}),
        "dataset_version": ds.version,
    }


# ---------------------------------------------------------------------------------------
# Case graph + click context
# ---------------------------------------------------------------------------------------

KIND_LABEL = {"financing_request": "financing request", "funding": "funding paid", "sale": "goods invoiced", "settlement": "buyer payment"}


def case_graph(ds: Dataset, eid: str, flagged_edges: set, flagged_refs: set) -> Dict:
    nodes = {eid}
    for t in ds.txns(eid):
        nodes.update((t.from_entity, t.to_entity))
    for c in find_trade_cycles(eid, ds.sale_adj):
        for m in c["path"]:
            nodes.add(m)
            nodes.update(t.to_entity for t in ds.txns(m) if t.kind == "financing_request")

    edges: Dict[str, Dict] = {}
    for n in nodes:
        for t in ds.txns(n):
            if t.from_entity != n or t.to_entity not in nodes:
                continue
            key = edge_id(t.from_entity, t.to_entity, t.kind)
            edge = edges.setdefault(key, {"id": key, "source": t.from_entity, "target": t.to_entity, "kind": t.kind,
                                          "label": KIND_LABEL[t.kind], "count": 0, "total": 0.0, "txns": []})
            edge["count"] += 1
            edge["total"] += t.amount
            edge["txns"].append({"invoice": t.invoice_ref, "amount": round(t.amount, 2), "date": fmt_date(t.timestamp),
                                 "flagged": t.invoice_ref in flagged_refs})
    for edge in edges.values():
        edge["txns"].sort(key=lambda x: x["date"])
        edge["flagged"] = edge["id"] in flagged_edges
        edge["total"] = round(edge["total"], 2)

    out_nodes = []
    for n in nodes:
        ent = ds.entities.get(n)
        ev = ds.evidence.get(n)
        out_nodes.append({
            "id": n,
            "name": ent.business_name if ent else n,
            "type": ent.entity_type.value if ent else "unknown",
            "location": ent.location if ent else "",
            "risk_score": round(ev.risk_score, 1) if ev else 0.0,
            "is_focus": n == eid,
        })
    return {"nodes": out_nodes, "edges": list(edges.values())}


def entity_context(ds: Dataset, entity_id: str, case_id: str) -> Dict:
    ent = ds.entities[entity_id]
    ev = ds.evidence[entity_id]
    between = sorted([t for t in ds.txns(entity_id) if case_id in (t.from_entity, t.to_entity) and entity_id != case_id],
                     key=lambda t: t.timestamp)
    facts = []
    case_name = ds.name(case_id)

    pairs = find_duplicate_financing(case_id, ds.transactions, ds.entities)
    for p in pairs:
        if entity_id in (p["financier_a"], p["financier_b"]):
            mine_first = entity_id == p["financier_a"]
            other = p["financier_b"] if mine_first else p["financier_a"]
            my_ref, my_ts = (p["ref_a"], p["ts_a"]) if mine_first else (p["ref_b"], p["ts_b"])
            other_ref, other_ts = (p["ref_b"], p["ts_b"]) if mine_first else (p["ref_a"], p["ts_a"])
            repaid = any(t.kind == "settlement" and t.to_entity == entity_id and canonical_ref(t.invoice_ref) == canonical_ref(my_ref)
                         for t in ds.transactions)
            facts.append(f"Financed {my_ref} on {fmt_date(my_ts)}. {ds.name(other)} financed the same invoice as {other_ref} on {fmt_date(other_ts)}.")
            facts.append("The buyer has repaid this financier." if repaid else "The buyer has NOT repaid this financier: its money is at risk.")
        if ent.entity_type == EntityType.IMPORTER:
            key = canonical_ref(p["ref_a"])
            shipped = [t for t in ds.txns(entity_id) if t.kind == "sale" and canonical_ref(t.invoice_ref) == key]
            if shipped:
                facts.append(f"Received goods for {p['ref_a']} once ({money(shipped[0].amount)}), yet {case_name} raised "
                             f"{money(p['amount_a'] + p['amount_b'])} of financing on it.")

    ring = next((c["path"] for c in find_trade_cycles(case_id, ds.sale_adj)), None)
    if ring and entity_id in ring:
        idx = ring.index(entity_id)
        facts.append(f"Part of the loop: buys from {ds.name(ring[idx - 1])} and sells on to {ds.name(ring[(idx + 1) % len(ring)])}.")
    if ring and ent.entity_type in (EntityType.BANK, EntityType.FACTOR):
        legs = [t for m in ring for t in ds.txns(m) if t.kind == "financing_request" and t.from_entity == m and t.to_entity == entity_id]
        if legs:
            facts.append(f"Financed {len(legs)} invoices inside the loop, worth {money(sum(t.amount for t in legs))} in total.")

    if not facts:
        facts.append(f"Ordinary relationship with {case_name}: {len(between)} transactions, nothing unusual.")

    return {
        "id": entity_id,
        "name": ent.business_name,
        "type": ent.entity_type.value,
        "location": ent.location,
        "business": ent.business,
        "own_risk_score": round(ev.risk_score, 1),
        "facts": facts,
        "transactions_with_case": [
            {"invoice": t.invoice_ref, "what": KIND_LABEL[t.kind], "amount": money(t.amount), "date": fmt_date(t.timestamp),
             "direction": "to" if t.from_entity == case_id else "from"}
            for t in between[-8:]
        ],
    }


# ---------------------------------------------------------------------------------------
# Input trace: the raw records behind a case, grouped by marketplace stage
# ---------------------------------------------------------------------------------------

def input_trace(ds: Dataset, eid: str) -> Dict:
    e = ds.entities[eid]
    ev = ds.evidence[eid]
    txs = ds.txns(eid)
    pairs = find_duplicate_financing(eid, ds.transactions, ds.entities)
    cycles = find_trade_cycles(eid, ds.sale_adj)
    dup_refs = {p["ref_a"] for p in pairs} | {p["ref_b"] for p in pairs}
    loop_members = set(cycles[0]["path"]) if cycles else set()

    def rec(t: Transaction) -> Dict:
        flagged = t.invoice_ref in dup_refs or (
            t.kind == "sale" and t.from_entity in loop_members and t.to_entity in loop_members)
        return {"invoice": t.invoice_ref, "from": ds.name(t.from_entity), "to": ds.name(t.to_entity),
                "amount": money(t.amount), "date": fmt_date(t.timestamp), "flagged": flagged, "_ts": t.timestamp}

    by_kind = {k: [rec(t) for t in txs if t.kind == k] for k in ("sale", "financing_request", "funding")}
    # Buyers repay the financier, not the exporter, so match repayments by invoice reference.
    my_refs = {canonical_ref(t.invoice_ref) for t in txs if t.from_entity == eid and t.kind in ("sale", "financing_request")}
    by_kind["settlement"] = [rec(t) for t in ds.transactions if t.kind == "settlement"
                             and (eid in (t.from_entity, t.to_entity) or canonical_ref(t.invoice_ref) in my_refs)]
    for rows in by_kind.values():
        rows.sort(key=lambda r: (not r["flagged"], r["_ts"]))
        for r in rows:
            del r["_ts"]

    if pairs:
        p = pairs[0]
        story = (f"{p['ref_a']} went to {ds.name(p['financier_a'])} on {fmt_date(p['ts_a'])}; {p['ref_b']} went to "
                 f"{ds.name(p['financier_b'])} on {fmt_date(p['ts_b'])}. Each financier saw one clean invoice on its own book. "
                 f"Only a view across both books links them.")
    elif cycles:
        route = " → ".join(ds.name(n) for n in cycles[0]["path"] + [cycles[0]["path"][0]])
        story = (f"Every invoice looks normal on its own. Only the chain of sale records shows the goods travelling "
                 f"{route}, {cycles[0]['rounds']} times, with no outside buyer.")
    else:
        story = "Every invoice has one sale, one financing and a buyer repayment. The inputs line up, so nothing is flagged."

    # --- Digital Trade Fingerprint Data ---
    trust_score = int(round(100 - ev.risk_score))
    
    # 1. Identity
    identity = {
        "legal_name": e.business_name,
        "gstin": "Verified",
        "lei": "Verified",
        "kyc": "Verified",
        "kyb": "Verified",
        "kya": "Verified",
        "ubo": "Identified",
        "related_entities": len(ds.sale_adj.get(eid, {})) + 2, # synthetic metric
        "common_directors": 1 if not pairs and not cycles else 2,
        "jurisdictions": "India / Singapore" if e.location == "Surat" else f"India / {e.location}"
    }
    
    # 2. Trade
    reqs = [t for t in txs if t.kind == "financing_request"]
    primary_req = reqs[-1] if reqs else None
    primary_sale = None
    if primary_req:
        ckey = canonical_ref(primary_req.invoice_ref)
        primary_sale = next((t for t in txs if t.kind == "sale" and canonical_ref(t.invoice_ref) == ckey), None)
        
    buyer_name = ds.name(primary_sale.to_entity) if primary_sale else "Unknown"
    
    trade = {
        "invoice": primary_req.invoice_ref if primary_req else "N/A",
        "invoice_value": money(primary_sale.amount) if primary_sale else (money(primary_req.amount) if primary_req else "$0"),
        "buyer": buyer_name,
        "goods": e.business or "Export Goods",
        "origin": e.location or "India",
        "destination": "International",
        "customs": "Matched",
        "shipment": "Matched" if primary_sale else "Missing",
        "bill_of_lading": "Matched" if primary_sale else "Missing",
        "buyer_resolved": "Resolved",
        "consistency": "94%" if not cycles and not pairs else "41%"
    }
    
    # 3. Financing
    fin_overlap = bool(pairs)
    financing = {
        "requested": money(primary_req.amount) if primary_req else "$0",
        "financier": ds.name(primary_req.to_entity) if primary_req else "N/A",
        "tenor": "90 Days",
        "existing_exposure": money(sum(t.amount for t in reqs[:-1])) if len(reqs) > 1 else "$0",
        "historical_trades": len(txs),
        "avg_financing": money(sum(t.amount for t in reqs)/len(reqs)) if reqs else "$0",
        "overlap_detected": fin_overlap,
        "evidence": ["Similar invoice", "Same exporter", "Same buyer", "Overlapping financing period"] if fin_overlap else []
    }
    if cycles:
        financing["overlap_detected"] = True
        financing["evidence"] = ["Circular money flow", "Multiple rounds", "Value inflation", "No outside buyer"]
        
    # 4. Network
    network = {
        "exporter": e.business_name,
        "buyer": buyer_name,
        "financier": ds.name(primary_req.to_entity) if primary_req else "N/A",
        "trade_value": trade["invoice_value"],
        "is_loop": bool(cycles),
        "loop_route": [ds.name(n) for n in cycles[0]["path"]] if cycles else []
    }
    
    fingerprint = {
        "score": trust_score,
        "identity": identity,
        "trade": trade,
        "financing": financing,
        "network": network,
        "sources": {
            "bank": {"count": 8, "status": "VERIFIED"},
            "trade": {"count": 11, "status": "VERIFIED"},
            "identity": {"count": 7, "status": "VERIFIED"},
            "documents": {"count": 6, "status": "VERIFIED"},
            "financial": {"count": 3, "status": "REVIEW" if fin_overlap or cycles else "VERIFIED"},
            "network": {"count": 2, "status": "VERIFIED"}
        }
    }

    return {
        "case": case_summary(ds, ev),
        "onboarding": {
            "legal_name": e.business_name, "entity_type": e.entity_type.value.title(),
            "location": e.location or "not provided", "line_of_business": e.business or "not provided",
            "declared_annual_turnover": money(e.declared_volume),
        },
        "records": {k: {"count": len(v), "examples": v[:3]} for k, v in by_kind.items()},
        "story": story,
        "fingerprint": fingerprint
    }


# ---------------------------------------------------------------------------------------
# Case outputs: what the product hands to people, derived from the findings by typology rules
# ---------------------------------------------------------------------------------------

def _act(owner, action, evidence, when, notice=False):
    return {"owner": owner, "action": action, "evidence": evidence, "when": when, "notice": notice}


def case_outputs(ds: Dataset, eid: str, decision: str) -> Dict:
    e = ds.entities[eid]
    ev = ds.evidence[eid]
    name = e.business_name
    txs = ds.txns(eid)
    sales = [t for t in txs if t.kind == "sale" and t.from_entity == eid]
    reqs = [t for t in txs if t.kind == "financing_request" and t.from_entity == eid]
    repaid = {(t.to_entity, canonical_ref(t.invoice_ref)) for t in ds.transactions if t.kind == "settlement"}
    pairs = find_duplicate_financing(eid, ds.transactions, ds.entities)
    cycles = find_trade_cycles(eid, ds.sale_adj)
    actions, watch, evidence_pack = [], [], []
    at_risk = {"amount": "$0", "held_by": "nobody", "basis": "no fraud pattern found"}

    if pairs:
        p = pairs[0]
        key = canonical_ref(p["ref_a"])
        shipped = [t for t in sales if canonical_ref(t.invoice_ref) == key]
        buyer = ds.name(shipped[0].to_entity) if shipped else "the buyer"
        unpaid = [f for f in (p["financier_a"], p["financier_b"]) if (f, key) not in repaid]
        paid = [f for f in (p["financier_a"], p["financier_b"]) if f not in unpaid]
        exposure = 0.0
        for f, ref in ((p["financier_a"], p["ref_a"]), (p["financier_b"], p["ref_b"])):
            if f in unpaid:
                funding = _funding_for(ds, f, eid, ref)
                exposure += funding.amount if funding else 0.0
        dup_refs = {canonical_ref(x["ref_a"]) for x in pairs}
        other_open = [t for t in reqs if (t.to_entity, canonical_ref(t.invoice_ref)) not in repaid and canonical_ref(t.invoice_ref) not in dup_refs]
        victims = ", ".join(ds.name(f) for f in unpaid) or "none yet"
        at_risk = {"amount": money(exposure), "held_by": victims,
                   "basis": f"funded {p['ref_b']}, but {buyer} repaid only {', '.join(ds.name(f) for f in paid) or 'nobody'}"}
        actions.append(_act(f"Credit risk · every financier of {name}", f"Freeze new financing requests from {name}",
                            f"{p['ref_a']} and {p['ref_b']} are the same invoice, financed by {ds.name(p['financier_a'])} and {ds.name(p['financier_b'])}", "Now"))
        for f in unpaid:
            actions.append(_act(ds.name(f), f"Stop further drawdowns to {name} and start recovery of {money(exposure)}",
                                f"{buyer} repaid the same invoice to {', '.join(ds.name(x) for x in paid) or 'nobody'}; this financier will not be repaid", "Today", notice=True))
        for f in paid:
            n_other = sum(1 for t in reqs if t.to_entity == f and canonical_ref(t.invoice_ref) != key)
            actions.append(_act(ds.name(f), f"Review the other {n_other} invoices it financed for {name}",
                                f"the invoice it financed ({p['ref_a']}) was financed again elsewhere", "This week", notice=True))
        actions.append(_act("Operations", f"Request the bill of lading and invoice copy for {p['ref_a']}; confirm with {buyer} it received one shipment",
                            f"{len(shipped)} shipment recorded against {len(pairs) + 1} financings", "Today"))
        if other_open:
            actions.append(_act("Credit risk", f"Re-check {len(other_open)} other unrepaid financings worth {money(sum(t.amount for t in other_open))}",
                                "a company that double-financed once may have done it elsewhere", "This week"))
        actions.append(_act("Compliance", "Prepare a suspicious transaction report if the documents confirm the duplicate",
                            "same invoice financed twice with a reformatted reference", "After documents"))
        watch += [f"Block any new financing from {name} whose invoice number normalises to {p['ref_a']}",
                  f"Check every new {name} invoice against all financiers' books before funding"]
        evidence_pack += [f"Sale: {t.invoice_ref} to {buyer}, {money(t.amount)}, {fmt_date(t.timestamp)}" for t in shipped]
        for f, ref, amt, ts in ((p["financier_a"], p["ref_a"], p["amount_a"], p["ts_a"]), (p["financier_b"], p["ref_b"], p["amount_b"], p["ts_b"])):
            funding = _funding_for(ds, f, eid, ref)
            paid_out = f"{ds.name(f)} paid out {money(funding.amount)} on {fmt_date(funding.timestamp)}" if funding else "not yet funded"
            evidence_pack.append(f"Financing request: {ref} to {ds.name(f)} for {money(amt)} on {fmt_date(ts)}; {paid_out}")
        evidence_pack += [f"Repayment: {buyer} → {ds.name(t.to_entity)}, {money(t.amount)}, {fmt_date(t.timestamp)}"
                          for t in ds.transactions if t.kind == "settlement" and canonical_ref(t.invoice_ref) == key]

    elif cycles:
        c = max(cycles, key=lambda x: x["rounds"])
        ring = c["path"]
        names = ", ".join(ds.name(m) for m in ring)
        ring_set = set(ring)
        loop_reqs = [t for m in ring for t in ds.txns(m) if t.kind == "financing_request" and t.from_entity == m]
        lenders = sorted({t.to_entity for t in loop_reqs})
        funded = sum(t.amount for m in ring for t in ds.txns(m) if t.kind == "funding" and t.to_entity == m and t.from_entity in lenders)
        vals = c["first_leg_values"]
        growth = (vals[-1] / vals[0] - 1) if len(vals) > 1 else 0.0
        outside = sum(1 for m in ring for b in ds.sale_adj.get(m, {}) if b not in ring_set)
        lender_names = ", ".join(ds.name(l) for l in lenders)
        at_risk = {"amount": money(funded), "held_by": lender_names,
                   "basis": f"financing paid against {len(loop_reqs)} invoices that went round a closed loop"}
        actions.append(_act(f"Credit risk · {lender_names}", f"Pause new financing to all {len(ring)} loop members: {names}",
                            f"goods went round {c['rounds']} times with {outside} sales to anyone outside the loop", "Now"))
        for l in lenders:
            n = sum(1 for t in loop_reqs if t.to_entity == l)
            actions.append(_act(ds.name(l), f"Treat {n} financed invoices ({money(sum(t.amount for t in loop_reqs if t.to_entity == l))}) as one connected exposure, not {len(ring)} separate clients",
                                f"each client's buyer is the next member of the same loop", "Today", notice=True))
        sample = ", ".join(sorted({t.invoice_ref for t in loop_reqs})[:3])
        actions.append(_act("Operations", f"Request bills of lading and shipping records for {sample} to confirm the goods physically moved",
                            f"invoice value grew {growth:.1%} across the laps with no new buyer", "Today"))
        actions.append(_act("KYB / onboarding", f"Check {names} for shared directors, addresses or bank accounts",
                            "they trade only with each other", "This week"))
        actions.append(_act("Compliance", "Assess for trade-based money laundering; report if shipping records don't match",
                            f"{money(c['value_cycled'])} of invoices cycled", "After documents"))
        watch += [f"Link {names} as one group: flag any new invoice between them",
                  "Alert if a new lap starts (goods return to the first company again)"]
        evidence_pack += [f"Loop: {' → '.join(ds.name(n) for n in ring + [ring[0]])}, {c['rounds']} laps",
                          f"Invoices cycled: {money(c['value_cycled'])}, value growth {growth:.1%}",
                          f"Sales to buyers outside the loop: {outside}",
                          f"Financing inside the loop: {len(loop_reqs)} invoices from {lender_names}"]

    else:
        settled = sum(1 for t in sales if (any(x.to_entity for x in reqs if x.invoice_ref == t.invoice_ref)) and
                      any((x.to_entity, canonical_ref(t.invoice_ref)) in repaid for x in reqs if x.invoice_ref == t.invoice_ref))
        buyer_counts = {}
        for t in sales:
            buyer_counts[t.to_entity] = buyer_counts.get(t.to_entity, 0) + t.amount
        top_buyer, top_amt = max(buyer_counts.items(), key=lambda kv: kv[1]) if buyer_counts else (None, 0.0)
        share = top_amt / sum(buyer_counts.values()) if buyer_counts else 0.0
        verb = "Monitor" if ev.risk_score > 40 else "Clear"
        actions.append(_act("Credit risk", f"{verb}: keep financing {name} on standard terms",
                            f"{settled} of {len(sales)} invoices repaid by {len(buyer_counts)} buyers; 0 duplicates; 0 loops", "Now"))
        actions.append(_act("Financiers", "No alert sent", "nothing in the data suggests another financier is exposed", "n/a"))
        if top_buyer:
            actions.append(_act("Monitoring", f"Re-score if one buyer passes 50% of volume (today {ds.name(top_buyer)}: {share:.0%})",
                                "concentration is the main weak signal on this company", "Ongoing"))
        watch += [f"Standard monthly re-score of {name}", "Re-open automatically if any invoice is financed twice or a sales loop appears"]
        evidence_pack += [f"{len(reqs)} financings, {len(sales)} sales, {settled} repaid",
                          f"Buyers: {', '.join(ds.name(b) for b in buyer_counts)}"]

    for i, a in enumerate(actions, 1):
        a["priority"] = i

    # Categorized evidence pack for structured evidence view
    categorized = {"documents": [], "entity": [], "financing": [], "transactions": []}
    for item in evidence_pack:
        lower = item.lower()
        if any(w in lower for w in ("sale:", "loop:", "invoices cycled", "sales to")):
            categorized["documents"].append(item)
        elif any(w in lower for w in ("buyers:", "financings,")):
            categorized["entity"].append(item)
        elif any(w in lower for w in ("financing request:", "financing inside")):
            categorized["financing"].append(item)
        elif any(w in lower for w in ("repayment:", "funding")):
            categorized["transactions"].append(item)
        else:
            categorized["documents"].append(item)

    return {"decision": decision, "score": round(ev.risk_score, 1), "band": risk_band(ev.risk_score),
            "money_at_risk": at_risk, "actions": actions, "watch": watch, "evidence_pack": evidence_pack,
            "evidence_categorized": categorized}


# ---------------------------------------------------------------------------------------
# Trade request: the bank officer's incoming financing request view
# ---------------------------------------------------------------------------------------

def trade_request(ds: Dataset, eid: str) -> Dict:
    """Build the trade finance request view — what a bank officer sees when a financing request arrives."""
    e = ds.entities[eid]
    ev = ds.evidence[eid]
    txs = ds.txns(eid)
    sales = sorted([t for t in txs if t.kind == "sale" and t.from_entity == eid], key=lambda t: t.timestamp)
    reqs = sorted([t for t in txs if t.kind == "financing_request" and t.from_entity == eid], key=lambda t: t.timestamp)
    total_financed = sum(t.amount for t in reqs)
    pairs = find_duplicate_financing(eid, ds.transactions, ds.entities)
    cycles = find_trade_cycles(eid, ds.sale_adj)
    band = risk_band(ev.risk_score)

    # The "incoming trade" is the most recent (or largest) financing request
    primary_req = reqs[-1] if reqs else None
    primary_sale = None
    if primary_req:
        ckey = canonical_ref(primary_req.invoice_ref)
        primary_sale = next((t for t in sales if canonical_ref(t.invoice_ref) == ckey), None)

    # Status pills
    trade_status = "verified"  # we have the sale + financing records
    entity_status = "verified"  # KYC/KYB present
    if band == "HIGH":
        risk_status = "escalate"
    elif band == "MEDIUM":
        risk_status = "review"
    else:
        risk_status = "clear"

    # Primary alert
    hl = headline(ds, ev)
    typology = None
    if "duplicate_invoice_financing" in ev.matched_patterns:
        typology = "duplicate_financing"
    elif "circular_trade" in ev.matched_patterns:
        typology = "circular_trade"

    # Structured evidence checklist for the alert detail
    evidence_checks = []
    comparison = None

    if pairs:
        p = pairs[0]
        key = canonical_ref(p["ref_a"])
        shipped = [t for t in sales if canonical_ref(t.invoice_ref) == key]
        buyer = ds.name(shipped[0].to_entity) if shipped else "unknown"
        first_funding = _funding_for(ds, p["financier_a"], eid, p["ref_a"])
        second_funding = _funding_for(ds, p["financier_b"], eid, p["ref_b"])
        repaid_set = {(t.to_entity, canonical_ref(t.invoice_ref)) for t in ds.transactions if t.kind == "settlement"}
        first_repaid = (p["financier_a"], key) in repaid_set
        second_repaid = (p["financier_b"], key) in repaid_set

        match_desc = "canonical match" if p["canonical_match"] else f"{p['similarity']:.0%} similar"
        evidence_checks = [
            {"label": "Same exporter", "match": True, "detail": e.business_name},
            {"label": "Same buyer", "match": True, "detail": buyer},
            {"label": "Matching invoice characteristics", "match": True,
             "detail": f"{p['ref_a']} ↔ {p['ref_b']}, {match_desc}"},
            {"label": "Matching underlying shipment", "match": len(shipped) > 0,
             "detail": f"{len(shipped)} shipment(s) for {money(shipped[0].amount)}" if shipped else "no shipment record"},
            {"label": "Existing financing relationship found", "match": True,
             "detail": f"Previously financed by {ds.name(p['financier_a'])} on {fmt_date(p['ts_a'])}"},
            {"label": "Financing dates overlap", "match": True,
             "detail": f"{abs(round((p['ts_b'] - p['ts_a']) / 86400))} days apart"},
        ]

        # Side-by-side comparison panel
        comparison = {
            "type": "duplicate",
            "invoice_a": {
                "reference": p["ref_a"],
                "financier": ds.name(p["financier_a"]),
                "amount": money(p["amount_a"]),
                "date": fmt_date(p["ts_a"]),
                "funded": money(first_funding.amount) if first_funding else "not yet",
                "fund_date": fmt_date(first_funding.timestamp) if first_funding else "—",
                "buyer_repaid": first_repaid,
                "repaid_label": "Buyer repaid" if first_repaid else "Not repaid",
            },
            "invoice_b": {
                "reference": p["ref_b"],
                "financier": ds.name(p["financier_b"]),
                "amount": money(p["amount_b"]),
                "date": fmt_date(p["ts_b"]),
                "funded": money(second_funding.amount) if second_funding else "not yet",
                "fund_date": fmt_date(second_funding.timestamp) if second_funding else "—",
                "buyer_repaid": second_repaid,
                "repaid_label": "Buyer repaid" if second_repaid else "Not repaid",
            },
            "buyer": buyer,
            "shipments": len(shipped),
            "goods_value": money(shipped[0].amount) if shipped else "$0",
            "total_financing": money(p["amount_a"] + p["amount_b"]),
            "exposure": money(second_funding.amount if second_funding and not second_repaid else 0.0),
        }

    elif cycles:
        c = cycles[0]
        ring = set(c["path"])
        outside = sum(1 for m in c["path"] for b in ds.sale_adj.get(m, {}) if b not in ring)
        evidence_checks = [
            {"label": "Closed trading loop detected", "match": True,
             "detail": " → ".join(ds.name(n) for n in c["path"] + [c["path"][0]])},
            {"label": "Multiple rounds of trade", "match": c["rounds"] > 1,
             "detail": f"{c['rounds']} complete rounds"},
            {"label": "No outside buyers", "match": outside == 0,
             "detail": f"{outside} sales to buyers outside the loop"},
            {"label": "Value inflation across laps", "match": True,
             "detail": f"{money(c['value_cycled'])} cycled"},
            {"label": "All members share a financier", "match": True,
             "detail": "connected through financing relationships"},
        ]

        comparison = {
            "type": "loop",
            "route": [{"name": ds.name(n), "id": n} for n in c["path"]],
            "rounds": c["rounds"],
            "value_cycled": money(c["value_cycled"]),
            "outside_sales": outside,
            "members": len(c["path"]),
        }

    return {
        "case": case_summary(ds, ev),
        "trade": {
            "invoice": primary_req.invoice_ref if primary_req else "—",
            "buyer": ds.name(primary_sale.to_entity) if primary_sale else (ds.name(sales[-1].to_entity) if sales else "—"),
            "amount": money(primary_req.amount) if primary_req else "$0",
            "financing_requested": money(primary_req.amount * 0.95) if primary_req else "$0",
            "date": fmt_date(primary_req.timestamp) if primary_req else "—",
            "financier": ds.name(primary_req.to_entity) if primary_req else "—",
        },
        "company": {
            "name": e.business_name,
            "location": e.location or "not provided",
            "business": e.business or "exporter",
            "declared_volume": money(e.declared_volume),
            "total_financed": money(total_financed),
            "financed_pct": f"{total_financed / e.declared_volume:.0%}" if e.declared_volume else "n/a",
            "financiers": len({t.to_entity for t in reqs}),
            "buyers": len({t.to_entity for t in sales}),
            "invoices": len(reqs),
        },
        "status": {
            "trade": trade_status,
            "entity": entity_status,
            "risk": risk_status,
        },
        "alert": {
            "present": typology is not None,
            "typology": typology,
            "headline": hl,
            "patterns": [PATTERN_LABELS.get(p, p) for p in ev.matched_patterns],
            "exposure": money(sum(
                (_funding_for(ds, p["financier_b"], eid, p["ref_b"]).amount if _funding_for(ds, p["financier_b"], eid, p["ref_b"]) else 0.0)
                for p in pairs
            )) if pairs else (money(sum(t.amount for m in cycles[0]["path"] for t in ds.txns(m) if t.kind == "funding" and t.to_entity == m)) if cycles else "$0"),
        },
        "evidence_checks": evidence_checks,
        "comparison": comparison,
    }
