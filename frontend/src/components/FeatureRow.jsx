const features = [
  {
    title: 'Behavioral graph, not document checks',
    text: 'Traditional trade-finance systems validate one invoice at a time. Trade Sentinel connects exporters, factors, banks and invoices into one graph and scores relationships.',
  },
  {
    title: 'Explainable evidence, every flag',
    text: 'Every risk score traces back to specific transactions, invoice references, and counterparties — never a black-box number.',
  },
  {
    title: 'Production precedent',
    text: 'MonetaGo already detects duplicate invoice financing across India’s TReDS exchanges. Trade Sentinel adds the behavioral-graph layer on top.',
  },
];

export default function FeatureRow() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 24,
        padding: '20px 24px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
      }}
    >
      {features.map((f) => (
        <div key={f.title}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{f.title}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>{f.text}</div>
        </div>
      ))}
    </div>
  );
}
