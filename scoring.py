from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from data_gen import generate_dataset, Entity, Transaction, EntityType
from difflib import SequenceMatcher

# Lightweight graph implementation (no networkx dependency)
class MultiDiGraph:
    def __init__(self):
        self._out = {}
        self._in = {}
        self._edges = []

    def add_edge(self, from_node, to_node, weight=1, timestamp=0, invoice_ref=""):
        if from_node not in self._out:
            self._out[from_node] = {}
        if to_node not in self._in:
            self._in[to_node] = {}

        if to_node not in self._out[from_node]:
            self._out[from_node][to_node] = []
        if from_node not in self._in[to_node]:
            self._in[to_node][from_node] = []

        self._out[from_node][to_node].append(weight)
        self._in[to_node][from_node].append(weight)
        self._edges.append((from_node, to_node, weight, timestamp, invoice_ref))

    def __contains__(self, node):
        return node in self._out or node in self._in

    def successors(self, node):
        return list(self._out.get(node, {}).keys())

    def predecessors(self, node):
        return list(self._in.get(node, {}).keys())

    def in_degree(self, node):
        return len(self._in.get(node, {}))

    def out_degree(self, node):
        return len(self._out.get(node, {}))

    def out_edges(self, node, data=False):
        edges = [(node, target) for target in self._out.get(node, {})]
        if data:
            return [(node, target, {"weight": sum(self._out[node][target])}) for target in self._out.get(node, {})]
        return edges

    def in_edges(self, node, data=False):
        edges = [(source, node) for source in self._in.get(node, {})]
        if data:
            return [(source, node, {"weight": sum(self._in[node][source])}) for source in self._in.get(node, {})]
        return edges

    def get_invoices_for_entity(self, entity_id):
        """Return all invoice refs for transactions involving this entity"""
        invoices = []
        for src, dst, weight, ts, inv_ref in self._edges:
            if src == entity_id or dst == entity_id:
                invoices.append(inv_ref)
        return invoices

    def nodes(self):
        all_nodes = set(self._out.keys()) | set(self._in.keys())
        return list(all_nodes)

@dataclass
class EntityEvidence:
    entity_id: str
    entity_type: str
    business_name: str
    risk_score: float
    features: Dict[str, float]
    matched_patterns: List[str]
    is_fraudulent: bool
    counterparty_entities: List[str] = field(default_factory=list)
    suspicious_invoices: List[Tuple[str, str, float]] = field(default_factory=list)

RISK_WEIGHTS = {
    "duplicate_invoice_match": 0.35,
    "fan_in_out": 0.18,
    "velocity": 0.16,
    "pass_through_ratio": 0.12,
    "pagerank_shift": 0.10,
    "kyc_volume_mismatch": 0.05,
    "dormancy_burst": 0.02,
    "short_cycle": 0.02,
}

def fuzzy_match_invoices(inv1: str, inv2: str, threshold: float = 0.75) -> Tuple[bool, float]:
    """Fuzzy match two invoice references; return (is_match, similarity_score)"""
    if inv1 == inv2:
        return True, 1.0

    # Normalize: remove common prefixes/suffixes
    norm1 = inv1.replace("INV_", "").replace("_v2", "").replace("_v3", "")
    norm2 = inv2.replace("INV_", "").replace("_v2", "").replace("_v3", "")

    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    is_match = similarity >= threshold
    return is_match, similarity

def compute_duplicate_invoice_match(entity_id: str, entities_dict: Dict, G: MultiDiGraph) -> Tuple[float, List]:
    """Detect duplicate invoice financing across multiple factors/financiers"""
    if entity_id not in G:
        return 0.0, []

    invoices_by_ref = {}
    suspicious_invoices = []

    # Collect all invoices for this exporter across all transactions
    for src, dst, weight, ts, inv_ref in G._edges:
        if src == entity_id and inv_ref:
            if inv_ref not in invoices_by_ref:
                invoices_by_ref[inv_ref] = []
            invoices_by_ref[inv_ref].append((dst, weight, ts))

    # Look for invoices that appear multiple times to different factors
    duplicate_count = 0
    for inv_ref, destinations in invoices_by_ref.items():
        if len(destinations) >= 2:
            # Check if destination entities are different factors/banks
            unique_factors = set()
            for factor_id, amt, ts in destinations:
                if factor_id in entities_dict:
                    entity = entities_dict[factor_id]
                    if entity.entity_type in [EntityType.FACTOR, EntityType.BANK]:
                        unique_factors.add(factor_id)

            if len(unique_factors) >= 2:
                duplicate_count += 1
                total_duplicate_amount = sum(amt for _, amt, _ in destinations)
                suspicious_invoices.append((inv_ref, unique_factors, total_duplicate_amount))

    # Score: each duplicate invoice is a major red flag
    dup_match_score = min((duplicate_count / 1.0) * 100, 100)
    return dup_match_score, suspicious_invoices

def compute_fan_in_out(G: MultiDiGraph, entity_id: str) -> float:
    """Fan-in/fan-out: suspicious when many entities converge on one"""
    in_degree = G.in_degree(entity_id)
    out_degree = G.out_degree(entity_id)

    total = in_degree + out_degree
    if total == 0:
        return 0.0

    ratio = max(in_degree, out_degree) / total if total > 0 else 0.0
    return ratio * 100

def compute_velocity(G: MultiDiGraph, entity_id: str) -> float:
    """Transaction velocity: rapid volume in short time window"""
    if entity_id not in G:
        return 0.0

    out_edges = [(u, v) for u, v in G.out_edges(entity_id)]
    in_edges = [(u, v) for u, v in G.in_edges(entity_id)]

    total_txns = len(out_edges) + len(in_edges)
    velocity_score = min((total_txns / 30.0) * 100, 100)
    return velocity_score

def compute_pass_through_ratio(G: MultiDiGraph, entity_id: str) -> float:
    """Pass-through: funds routed through without retention"""
    in_degree = G.in_degree(entity_id)
    out_degree = G.out_degree(entity_id)

    if in_degree == 0:
        return 0.0

    ratio = out_degree / in_degree if in_degree > 0 else 0.0
    return min(ratio * 100, 100)

def compute_pagerank_shift(G: MultiDiGraph, entity_id: str) -> float:
    """Network position: suspicious if connected to low-trust entities"""
    if entity_id not in G:
        return 0.0

    def node_rank(node):
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        return (in_deg + 1) / (out_deg + in_deg + 2)

    successors = list(G.successors(entity_id))
    if not successors:
        return 0.0

    successor_ranks = [node_rank(s) for s in successors]
    avg_successor_rank = sum(successor_ranks) / len(successor_ranks)

    shift = (1.0 - avg_successor_rank) * 100
    return min(shift, 100)

def compute_kyc_volume_mismatch(declared_vol: float, G: MultiDiGraph, entity_id: str) -> float:
    """Observed activity vs declared business profile"""
    if entity_id not in G:
        actual_volume = 0.0
    else:
        out_edges = G.out_edges(entity_id, data=True)
        in_edges = G.in_edges(entity_id, data=True)

        out_vol = sum(data.get('weight', 0) for _, _, data in out_edges)
        in_vol = sum(data.get('weight', 0) for _, _, data in in_edges)
        actual_volume = out_vol + in_vol

    if declared_vol == 0:
        return 100.0 if actual_volume > 0 else 0.0

    ratio = actual_volume / declared_vol
    mismatch_score = min((ratio / 3.0) * 100, 100)
    return mismatch_score

def compute_dormancy_burst(G: MultiDiGraph, entity_id: str, transactions: List[Transaction]) -> float:
    """Dormant relationship suddenly active"""
    entity_txns = [tx for tx in transactions if tx.from_entity == entity_id or tx.to_entity == entity_id]

    if len(entity_txns) < 3:
        return 0.0

    sorted_txns = sorted(entity_txns, key=lambda x: x.timestamp)
    timestamps = [tx.timestamp for tx in sorted_txns]

    gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    if not gaps:
        return 0.0

    max_gap = max(gaps)
    max_gap_idx = gaps.index(max_gap)

    txns_before = len(sorted_txns[:max_gap_idx+1])
    txns_after = len(sorted_txns[max_gap_idx+1:])

    if txns_before == 0 or txns_after == 0:
        return 0.0

    burst_score = min((max_gap / 86400.0) * (txns_after / 10.0) * 10, 100)
    return burst_score if max_gap > 86400 else 0.0

def compute_short_cycle(G: MultiDiGraph, entity_id: str) -> float:
    """Circular invoicing/payment between related entities"""
    if entity_id not in G:
        return 0.0

    in_neighbors = set(G.predecessors(entity_id))
    out_neighbors = set(G.successors(entity_id))

    shared_peers = in_neighbors & out_neighbors
    if not shared_peers:
        return 0.0

    strong_cycles = 0
    for peer in shared_peers:
        in_count = len([src for src, dst in G.in_edges(entity_id) if src == peer])
        out_count = len([dst for src, dst in G.out_edges(entity_id) if dst == peer])
        if in_count >= 2 and out_count >= 2:
            strong_cycles += 1

    cycle_score = min((strong_cycles / 2.0) * 100, 100)
    return cycle_score

def score_entity(entity: Entity, entities_dict: Dict, G: MultiDiGraph, transactions: List[Transaction]) -> EntityEvidence:
    """Compute all features and produce risk score + evidence"""

    dup_invoice_score, suspicious_invoices = compute_duplicate_invoice_match(entity.entity_id, entities_dict, G)

    features = {
        "duplicate_invoice_match": dup_invoice_score,
        "fan_in_out": compute_fan_in_out(G, entity.entity_id),
        "velocity": compute_velocity(G, entity.entity_id),
        "pass_through_ratio": compute_pass_through_ratio(G, entity.entity_id),
        "pagerank_shift": compute_pagerank_shift(G, entity.entity_id),
        "kyc_volume_mismatch": compute_kyc_volume_mismatch(entity.declared_volume, G, entity.entity_id),
        "dormancy_burst": compute_dormancy_burst(G, entity.entity_id, transactions),
        "short_cycle": compute_short_cycle(G, entity.entity_id),
    }

    # Weighted combination
    risk_score = sum(features[key] * RISK_WEIGHTS[key] for key in features.keys())
    risk_score = min(risk_score, 100)

    # Pattern detection
    matched_patterns = []
    if features["duplicate_invoice_match"] > 20:
        matched_patterns.append("duplicate_invoice_financing")
    if features["fan_in_out"] > 65:
        matched_patterns.append("fan_in_out_concentration")
    if features["dormancy_burst"] > 60:
        matched_patterns.append("dormant_then_active")
    if features["short_cycle"] > 50:
        matched_patterns.append("circular_invoicing")
    if features["velocity"] > 65:
        matched_patterns.append("volume_spike")
    if features["kyc_volume_mismatch"] > 70:
        matched_patterns.append("kyc_mismatch")

    # Counterparties
    successors = list(G.successors(entity.entity_id))
    predecessors = list(G.predecessors(entity.entity_id))
    counterparties = list(set(successors + predecessors))[:10]

    return EntityEvidence(
        entity_id=entity.entity_id,
        entity_type=entity.entity_type.value,
        business_name=entity.business_name,
        risk_score=risk_score,
        features=features,
        matched_patterns=matched_patterns,
        is_fraudulent=entity.is_fraudulent,
        counterparty_entities=counterparties,
        suspicious_invoices=suspicious_invoices,
    )

def build_transaction_graph(transactions: List[Transaction]) -> MultiDiGraph:
    G = MultiDiGraph()
    for tx in transactions:
        G.add_edge(tx.from_entity, tx.to_entity, weight=tx.amount, timestamp=tx.timestamp, invoice_ref=tx.invoice_ref)
    return G

def score_all_entities(entities: List[Entity], transactions: List[Transaction]) -> List[EntityEvidence]:
    """Score all entities and return sorted by risk"""
    entities_dict = {e.entity_id: e for e in entities}
    G = build_transaction_graph(transactions)
    evidence_list = [score_entity(e, entities_dict, G, transactions) for e in entities]
    return sorted(evidence_list, key=lambda x: x.risk_score, reverse=True)

if __name__ == "__main__":
    print("Generating Trade Sentinel dataset...")
    entities, transactions = generate_dataset(n_normal_exporters=50, n_fraudulent_pairs=2)

    print(f"Generated {len(entities)} entities, {len(transactions)} transactions")

    print("\nScoring all entities...")
    evidence = score_all_entities(entities, transactions)

    print("\n=== SCORE BREAKDOWN BY GROUND TRUTH ===")
    fraudulent_scores = [e.risk_score for e in evidence if e.is_fraudulent]
    normal_scores = [e.risk_score for e in evidence if not e.is_fraudulent]

    print(f"\nFraudulent entities (n={len(fraudulent_scores)})")
    if fraudulent_scores:
        print(f"  Avg: {sum(fraudulent_scores)/len(fraudulent_scores):.1f}")
        print(f"  Min: {min(fraudulent_scores):.1f}, Max: {max(fraudulent_scores):.1f}")

    print(f"\nNormal entities (n={len(normal_scores)})")
    if normal_scores:
        print(f"  Avg: {sum(normal_scores)/len(normal_scores):.1f}")
        print(f"  Min: {min(normal_scores):.1f}, Max: {max(normal_scores):.1f}")

    print("\n=== TOP 10 HIGHEST-RISK ENTITIES ===")
    for e in evidence[:10]:
        label = "[FRAUD]" if e.is_fraudulent else "[NORMAL]"
        print(f"{label} {e.entity_id} ({e.entity_type}): {e.risk_score:.1f}")
        print(f"       Patterns: {e.matched_patterns}")
        if e.suspicious_invoices:
            print(f"       Suspicious invoices: {len(e.suspicious_invoices)}")
            for inv_ref, factors, amt in e.suspicious_invoices[:2]:
                print(f"         - {inv_ref}: ${amt:.0f} across {len(factors)} factors")

    print("\n=== ACTUAL FRAUDULENT ENTITIES ===")
    fraud_evidence = [e for e in evidence if e.is_fraudulent]
    for e in fraud_evidence:
        print(f"\n[FRAUD] {e.entity_id}: Risk {e.risk_score:.1f}")
        print(f"  Patterns: {e.matched_patterns}")
        print(f"  Suspicious invoices:")
        for inv_ref, factors, amt in e.suspicious_invoices:
            print(f"    - {inv_ref}: ${amt:.0f} to factors {factors}")
