"""Hand-authored synthetic scenarios layered on top of random background trade data.

All companies are fictional. Only the raw trade events are scripted here; every score,
flag and explanation is computed downstream by scoring.py / investigation.py.
"""
from typing import List, Tuple

from data_gen import Entity, EntityType, Transaction, generate_dataset

DAY = 86400

SCENARIO_LABELS = {
    "duplicate_financing": "Case A · Same invoice, two financiers",
    "circular_trade": "Case B · Goods going in circles",
    "clean_control": "Case C · Large but legitimate exporter",
}


class _Builder:
    def __init__(self):
        self.entities: List[Entity] = []
        self.transactions: List[Transaction] = []
        self._n = 0

    def entity(self, entity_id, etype, name, volume, location, business, scenario="", fraud=False, patterns=None):
        e = Entity(entity_id, etype, name, volume, fraud, patterns or [], location, business, scenario)
        self.entities.append(e)
        return entity_id

    def tx(self, src, dst, amount, ref, day, kind):
        self.transactions.append(Transaction(f"SCN_{self._n:05d}", src, dst, round(amount, 2), ref, int(day * DAY), kind=kind))
        self._n += 1

    def financed_sale(self, seller, buyer, financier, ref, amount, day, settle_day=None, settle_to=None):
        """One genuine trade: goods invoiced, invoice financed once, buyer settles the financier."""
        self.tx(seller, buyer, amount, ref, day, "sale")
        self.tx(seller, financier, amount, ref, day + 1, "financing_request")
        self.tx(financier, seller, amount * 0.95, ref, day + 2, "funding")
        if settle_day is not None:
            self.tx(buyer, settle_to or financier, amount, ref, settle_day, "settlement")


def build_scenarios() -> Tuple[List[Entity], List[Transaction]]:
    b = _Builder()

    # Shared financiers
    meridian = b.entity("FCT_MERIDIAN", EntityType.FACTOR, "Meridian Factor Co.", 40_000_000, "Mumbai", "Invoice factoring")
    harbour = b.entity("FCT_HARBOUR", EntityType.FACTOR, "Harbourline Trade Finance", 25_000_000, "GIFT City", "Receivables finance")
    keystone = b.entity("FCT_KEYSTONE", EntityType.FACTOR, "Keystone Receivables", 30_000_000, "Bengaluru", "Invoice factoring")
    coastal = b.entity("BNK_COASTAL", EntityType.BANK, "Coastal Commerce Bank", 90_000_000, "Mumbai", "Trade finance / LCs")

    # ---- Case A: duplicate invoice financing -------------------------------------------
    tapti = b.entity("EXP_TAPTI", EntityType.EXPORTER, "Tapti Loom Exports", 3_200_000, "Surat",
                     "Cotton fabric exporter", "duplicate_financing", True, ["duplicate_invoice_financing"])
    crescent = b.entity("IMP_CRESCENT", EntityType.IMPORTER, "Crescent Bay Trading", 6_000_000, "Dubai", "Textile wholesaler")
    portmoor = b.entity("IMP_PORTMOOR", EntityType.IMPORTER, "Portmoor Apparel", 4_500_000, "Leeds", "Garment maker")

    history = [  # 6 months of clean history before the fraud
        ("INV-2026-0402", crescent, meridian, 210_000, 5),
        ("INV-2026-0405", portmoor, keystone, 148_500, 14),
        ("INV-2026-0408", crescent, meridian, 265_000, 27),
        ("INV-2026-0410", portmoor, keystone, 132_750, 38),
        ("INV-2026-0412", crescent, meridian, 301_400, 49),
        ("INV-2026-0414", portmoor, keystone, 176_900, 58),
    ]
    for ref, buyer, fin, amt, day in history:
        b.financed_sale(tapti, buyer, fin, ref, amt, day, settle_day=day + 45)

    # The fraud: one shipment, one invoice, financed twice with a reformatted reference
    b.tx(tapti, crescent, 552_000, "INV-2026-0417", 72, "sale")
    b.tx(tapti, meridian, 552_000, "INV-2026-0417", 72, "financing_request")
    b.tx(meridian, tapti, 552_000 * 0.95, "INV-2026-0417", 73, "funding")
    b.tx(tapti, harbour, 552_000, "INV/2026/417", 74, "financing_request")
    b.tx(harbour, tapti, 552_000 * 0.95, "INV/2026/417", 75, "funding")
    b.tx(crescent, meridian, 552_000, "INV-2026-0417", 88, "settlement")  # buyer pays once

    # ---- Case B: circular trade (goods cycling through a ring) --------------------------
    opaline = b.entity("EXP_OPALINE", EntityType.EXPORTER, "Opaline Gems", 2_500_000, "Mumbai",
                       "Cut & polished diamonds", "circular_trade", True, ["circular_trade"])
    starfield = b.entity("EXP_STARFIELD", EntityType.EXPORTER, "Starfield Diamonds", 2_000_000, "Antwerp",
                         "Diamond trading", "circular_trade", True, ["circular_trade"])
    veridian = b.entity("EXP_VERIDIAN", EntityType.EXPORTER, "Veridian Jewels", 1_800_000, "Hong Kong",
                        "Jewellery trading", "circular_trade", True, ["circular_trade"])

    ring = [(opaline, starfield, "OPL"), (starfield, veridian, "STF"), (veridian, opaline, "VRD")]
    value = 1_200_000
    for rnd in range(4):
        for leg, (seller, buyer, prefix) in enumerate(ring):
            ref = f"{prefix}-{rnd + 1:03d}"
            day = 10 + rnd * 21 + leg * 4
            b.tx(seller, buyer, value, ref, day, "sale")
            b.tx(seller, coastal, value, ref, day + 1, "financing_request")
            b.tx(coastal, seller, value * 0.9, ref, day + 2, "funding")
            b.tx(buyer, seller, value, ref, day + 3, "settlement")
            value *= 1.02  # small markup each hop keeps invoices looking "new"

    # ---- Case C: large, busy, legitimate exporter ---------------------------------------
    northstar = b.entity("EXP_NORTHSTAR", EntityType.EXPORTER, "Northstar Agro Exports", 9_500_000, "Nashik",
                         "Grapes & onions exporter", "clean_control")
    buyers = [
        b.entity("IMP_FJORD", EntityType.IMPORTER, "Fjordline Fresh", 5_000_000, "Rotterdam", "Produce importer"),
        b.entity("IMP_SAHEL", EntityType.IMPORTER, "Sahel Foods", 3_000_000, "Riyadh", "Food distributor"),
        b.entity("IMP_MARINA", EntityType.IMPORTER, "Marina Greens", 3_500_000, "Singapore", "Grocery chain"),
        b.entity("IMP_ALDER", EntityType.IMPORTER, "Alder & Finch", 2_500_000, "London", "Retail importer"),
    ]
    financiers = [meridian, keystone]
    for i in range(18):
        buyer = buyers[i % len(buyers)]
        fin = financiers[i % 2]
        amt = 150_000 + i * 23_500 + (i % 3) * 11_000
        day = 3 + i * 5
        b.financed_sale(northstar, buyer, fin, f"NAE/{2026}/{101 + i}", amt, day, settle_day=day + 40)

    return b.entities, b.transactions


def build_demo_dataset(seed: int = 107, n_background: int = 40):
    """Scripted scenarios + random clean background exporters for realistic context."""
    bg_entities, bg_txns = generate_dataset(n_normal_exporters=n_background, n_fraudulent_pairs=0, seed=seed)
    sc_entities, sc_txns = build_scenarios()
    return bg_entities + sc_entities, bg_txns + sc_txns
