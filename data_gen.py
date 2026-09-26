import random
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class EntityType(str, Enum):
    EXPORTER = "exporter"
    IMPORTER = "importer"
    BANK = "bank"
    FACTOR = "factor"
    INVOICE = "invoice"

@dataclass
class Entity:
    entity_id: str
    entity_type: EntityType
    business_name: str
    declared_volume: float
    is_fraudulent: bool = False
    fraud_patterns: List[str] = None

@dataclass
class Transaction:
    tx_id: str
    from_entity: str
    to_entity: str
    amount: float
    invoice_ref: str
    timestamp: int
    is_flagged: bool = False

def generate_duplicate_invoice_pair(base_invoice_id: str, exporter_id: str, factor1_id: str, factor2_id: str,
                                     amount: float, timestamp: int, variation: str = "exact") -> List[Transaction]:
    """Generate a fraudulent duplicate invoice financing pair"""
    txns = []

    # Exporter → Factor1 with Invoice A
    invoice_ref = base_invoice_id
    if variation == "altered":
        invoice_ref = f"{base_invoice_id}_v2"
        amount = amount * random.uniform(0.95, 1.05)  # slightly altered amount

    txns.append(Transaction(
        tx_id=f"DUP_{base_invoice_id}_1",
        from_entity=exporter_id,
        to_entity=factor1_id,
        amount=amount,
        invoice_ref=invoice_ref,
        timestamp=timestamp
    ))

    # Exporter → Factor2 with same/similar Invoice A (the fraud)
    txns.append(Transaction(
        tx_id=f"DUP_{base_invoice_id}_2",
        from_entity=exporter_id,
        to_entity=factor2_id,
        amount=amount if variation != "altered" else amount * random.uniform(0.95, 1.05),
        invoice_ref=base_invoice_id,
        timestamp=timestamp + random.randint(3600, 86400*3)
    ))

    return txns

def generate_dataset(n_normal_exporters: int = 50, n_fraudulent_pairs: int = 2, seed: int = 42) -> tuple:
    random.seed(seed)

    entities: List[Entity] = []
    transactions: List[Transaction] = []
    tx_counter = 0
    current_time = 0

    # Create a stable set of importers, banks, factors
    importers = [Entity(f"IMP_{i:04d}", EntityType.IMPORTER, f"Importer {i}", random.uniform(100000, 5000000))
                 for i in range(30)]
    banks = [Entity(f"BNK_{i:03d}", EntityType.BANK, f"Bank {i}", random.uniform(1000000, 100000000))
             for i in range(10)]
    factors = [Entity(f"FCT_{i:04d}", EntityType.FACTOR, f"Factor {i}", random.uniform(500000, 50000000))
               for i in range(15)]

    entities.extend(importers)
    entities.extend(banks)
    entities.extend(factors)

    # Normal exporters with legitimate trade patterns
    normal_exporters = []
    for i in range(n_normal_exporters):
        exporter = Entity(
            entity_id=f"EXP_{i:04d}",
            entity_type=EntityType.EXPORTER,
            business_name=f"Exporter {i}",
            declared_volume=random.uniform(100000, 10000000),
            is_fraudulent=False
        )
        normal_exporters.append(exporter)
        entities.append(exporter)

        # Generate normal trade patterns: invoice → financing → payment
        num_invoices = random.randint(3, 15)
        for inv_idx in range(num_invoices):
            invoice_id = f"INV_{i:04d}_{inv_idx:03d}"
            amount = random.uniform(10000, 500000)
            importer = random.choice(importers)
            factor = random.choice(factors)

            # Exporter → Factor (financing request with invoice)
            transactions.append(Transaction(
                tx_id=f"TXN_{tx_counter:08d}",
                from_entity=exporter.entity_id,
                to_entity=factor.entity_id,
                amount=amount,
                invoice_ref=invoice_id,
                timestamp=current_time + random.randint(0, 86400*30)
            ))
            tx_counter += 1

            # Factor → Exporter (funding)
            transactions.append(Transaction(
                tx_id=f"TXN_{tx_counter:08d}",
                from_entity=factor.entity_id,
                to_entity=exporter.entity_id,
                amount=amount * 0.95,  # fee deducted
                invoice_ref=invoice_id,
                timestamp=current_time + random.randint(0, 86400*30)
            ))
            tx_counter += 1

    # Fraudulent exporters: duplicate invoice financing
    fraudulent_exporters = []
    for fraud_idx in range(n_fraudulent_pairs):
        exporter = Entity(
            entity_id=f"FRAUD_{fraud_idx:04d}",
            entity_type=EntityType.EXPORTER,
            business_name=f"Fraudulent Exporter {fraud_idx}",
            declared_volume=random.uniform(50000, 500000),
            is_fraudulent=True,
            fraud_patterns=["duplicate_invoice_financing"]
        )
        fraudulent_exporters.append(exporter)
        entities.append(exporter)

        # Mix of legitimate and duplicate invoices
        num_invoices = random.randint(5, 10)
        for inv_idx in range(num_invoices):
            base_invoice_id = f"FRAUD_INV_{fraud_idx:04d}_{inv_idx:03d}"
            amount = random.uniform(50000, 300000)

            # Randomly decide if this invoice is duplicated
            if inv_idx % 3 == 0 and inv_idx < num_invoices - 1:  # ~33% are duplicates
                # Duplicate financing: submit to 2 factors
                factor1 = random.choice(factors)
                factor2 = random.choice([f for f in factors if f.entity_id != factor1.entity_id])

                dup_txns = generate_duplicate_invoice_pair(
                    base_invoice_id,
                    exporter.entity_id,
                    factor1.entity_id,
                    factor2.entity_id,
                    amount,
                    current_time + random.randint(0, 86400*30),
                    variation=random.choice(["exact", "altered"])
                )
                transactions.extend(dup_txns)
                tx_counter += len(dup_txns)
            else:
                # Normal single financing
                factor = random.choice(factors)
                importer = random.choice(importers)

                transactions.append(Transaction(
                    tx_id=f"TXN_{tx_counter:08d}",
                    from_entity=exporter.entity_id,
                    to_entity=factor.entity_id,
                    amount=amount,
                    invoice_ref=base_invoice_id,
                    timestamp=current_time + random.randint(0, 86400*30)
                ))
                tx_counter += 1

                transactions.append(Transaction(
                    tx_id=f"TXN_{tx_counter:08d}",
                    from_entity=factor.entity_id,
                    to_entity=exporter.entity_id,
                    amount=amount * 0.95,
                    invoice_ref=base_invoice_id,
                    timestamp=current_time + random.randint(0, 86400*30)
                ))
                tx_counter += 1

    return entities, transactions
