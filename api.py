import os
import json
import random
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple

from data_gen import generate_dataset, Entity, Transaction
from scoring import score_all_entities, EntityEvidence

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
AGENT_PROMPT = Path(__file__).parent.joinpath("trade_sentinel_prompt.md").read_text()

app = FastAPI(title="Zeyro Trade Sentinel", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
current_entities: List[Entity] = []
current_transactions: List[Transaction] = []
current_evidence: List[EntityEvidence] = []

class EntityResponse(BaseModel):
    entity_id: str
    entity_type: str
    business_name: str
    risk_score: float
    features: Dict[str, float]
    matched_patterns: List[str]
    counterparty_entities: List[str]
    suspicious_invoices: List[Tuple[str, List[str], float]]

class GraphNode(BaseModel):
    id: str
    label: str
    risk_score: float
    entity_type: str
    title: str

class GraphEdge(BaseModel):
    source: str
    target: str
    amount: float
    invoice_ref: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

@app.on_event("startup")
def startup_event():
    """Initialize with synthetic data on startup"""
    regenerate_data(107)  # Hard-picked seed with clean fraud/normal separation

def regenerate_data(seed: int):
    """Regenerate dataset with given seed"""
    global current_entities, current_transactions, current_evidence

    entities, transactions = generate_dataset(n_normal_exporters=50, n_fraudulent_pairs=2, seed=seed)
    current_entities = entities
    current_transactions = transactions
    current_evidence = score_all_entities(entities, transactions)

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "entities": len(current_entities),
        "transactions": len(current_transactions),
        "product": "Zeyro Trade Sentinel"
    }

@app.get("/entities")
async def get_entities(limit: Optional[int] = None) -> List[EntityResponse]:
    """Get all entities ranked by trade finance risk"""
    if limit:
        evidence = current_evidence[:limit]
    else:
        evidence = current_evidence

    return [
        EntityResponse(
            entity_id=e.entity_id,
            entity_type=e.entity_type,
            business_name=e.business_name,
            risk_score=e.risk_score,
            features=e.features,
            matched_patterns=e.matched_patterns,
            counterparty_entities=e.counterparty_entities,
            suspicious_invoices=[(inv, list(factors), amt) for inv, factors, amt in e.suspicious_invoices],
        )
        for e in evidence
    ]

@app.get("/entities/{entity_id}")
async def get_entity_details(entity_id: str) -> Dict:
    """Get full Trade Sentinel evidence for one entity"""
    for evidence in current_evidence:
        if evidence.entity_id == entity_id:
            return {
                "entity_id": evidence.entity_id,
                "entity_type": evidence.entity_type,
                "business_name": evidence.business_name,
                "risk_score": evidence.risk_score,
                "features": evidence.features,
                "matched_patterns": evidence.matched_patterns,
                "counterparty_entities": evidence.counterparty_entities,
                "suspicious_invoices": [(inv, list(factors), amt) for inv, factors, amt in evidence.suspicious_invoices],
                "is_fraudulent": evidence.is_fraudulent,
                "risk_category": "HIGH_RISK" if evidence.risk_score > 70 else "MEDIUM_RISK" if evidence.risk_score > 40 else "LOW_RISK",
            }

    raise HTTPException(status_code=404, detail="Entity not found")

@app.get("/graph")
async def get_graph(limit: Optional[int] = 50) -> GraphResponse:
    """Get graph data for Trade Sentinel visualization (top N entities by risk)"""
    top_evidence = current_evidence[:limit]
    top_entities = {e.entity_id for e in top_evidence}

    # Build nodes with entity type coloring
    nodes = [
        GraphNode(
            id=e.entity_id,
            label=e.entity_id.replace("EXP_", "E").replace("IMP_", "I").replace("BNK_", "B").replace("FCT_", "F").replace("FRAUD_", "F!"),
            risk_score=e.risk_score,
            entity_type=e.entity_type,
            title=f"{e.business_name}: Trade Risk {e.risk_score:.1f}"
        )
        for e in top_evidence
    ]

    # Build edges from transactions
    edges = []
    seen_edges = set()

    for tx in current_transactions:
        if tx.from_entity in top_entities and tx.to_entity in top_entities:
            edge_key = (tx.from_entity, tx.to_entity)
            if edge_key not in seen_edges:
                edges.append(GraphEdge(
                    source=tx.from_entity,
                    target=tx.to_entity,
                    amount=tx.amount,
                    invoice_ref=tx.invoice_ref
                ))
                seen_edges.add(edge_key)

    return GraphResponse(nodes=nodes, edges=edges)

import time

WORKFLOW_PHASES = {
    "Counterparty": "Counterparty Intelligence (Before Approval)",
    "Transaction": "Transaction Intelligence (During Processing)",
    "Early Warning": "Behavioural Early Warning (During Monitoring)",
    "Investigation": "Explainable Investigation (When an Anomaly Appears)",
}

investigation_cache = {}  # {(entity_id, workflow): (note, timestamp)}
CACHE_TTL = 120  # 2 minutes

class InvestigateRequest(BaseModel):
    workflow: str = "Investigation"

@app.post("/investigate/{entity_id}")
async def investigate(entity_id: str, req: InvestigateRequest):
    """Generate a live investigation note by calling the Trade Sentinel agent (Groq) on current evidence"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured on the server")

    evidence = next((e for e in current_evidence if e.entity_id == entity_id), None)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    phase = WORKFLOW_PHASES.get(req.workflow, WORKFLOW_PHASES["Investigation"])

    cache_key = (entity_id, req.workflow)
    now = time.time()
    if cache_key in investigation_cache:
        cached_note, cached_time = investigation_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return {
                "entity_id": entity_id,
                "workflow": req.workflow,
                "note": cached_note,
                "model": GROQ_MODEL,
                "cached": True,
            }

    evidence_payload = {
        "entity_id": evidence.entity_id,
        "entity_type": evidence.entity_type,
        "business_name": evidence.business_name,
        "risk_score": round(evidence.risk_score, 1),
        "features": {k: round(v, 2) for k, v in evidence.features.items()},
        "matched_patterns": evidence.matched_patterns,
        "counterparty_entities": evidence.counterparty_entities,
        "suspicious_invoices": [
            {"invoice_ref": inv, "factors": list(factors), "amount": amt}
            for inv, factors, amt in evidence.suspicious_invoices
        ],
    }

    user_content = (
        f"Workflow phase requested: {phase}\n\n"
        f"Live behavioral evidence for this entity (computed just now from the current synthetic dataset):\n"
        f"{json.dumps(evidence_payload, indent=2)}\n\n"
        f"Write the investigation note for this entity in the '{phase}' template. "
        f"Use only the evidence given above — do not invent facts."
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": AGENT_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        note = data["choices"][0]["message"]["content"]
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Groq call failed: {exc}")

    investigation_cache[cache_key] = (note, time.time())
    return {
        "entity_id": entity_id,
        "workflow": req.workflow,
        "note": note,
        "model": GROQ_MODEL,
        "cached": False,
    }

@app.post("/regenerate")
async def regenerate(seed: Optional[int] = None):
    """Regenerate dataset with optional seed"""
    if seed is None:
        seed = random.randint(1, 100000)

    regenerate_data(seed)

    return {
        "message": "Trade Sentinel dataset regenerated",
        "seed": seed,
        "entities": len(current_entities),
        "transactions": len(current_transactions),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
