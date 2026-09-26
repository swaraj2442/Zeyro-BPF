from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
from data_gen import generate_dataset, Entity, Transaction
from scoring import score_all_entities, EntityEvidence
import random

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
    regenerate_data(42)

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
