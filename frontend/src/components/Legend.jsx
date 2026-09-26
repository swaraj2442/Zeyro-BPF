const riskLevels = [
  { label: 'Low risk', color: '#ffffff', border: '#d8d2c4' },
  { label: 'Medium risk', color: '#d8a559', border: '#b5813a' },
  { label: 'High risk', color: '#c1543f', border: '#8a2f22' },
];

const entityShapes = [
  { label: 'Exporter / Importer', shape: '●' },
  { label: 'Bank', shape: '■' },
  { label: 'Factor', shape: '▲' },
];

export default function Legend({ topRisk }) {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        boxShadow: 'var(--shadow-card)',
        fontSize: 12,
        display: 'flex',
        gap: 24,
      }}
    >
      <div>
        <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-muted)' }}>Risk</div>
        {riskLevels.map((r) => (
          <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: r.color,
                border: `1.5px solid ${r.border}`,
                display: 'inline-block',
              }}
            />
            {r.label}
          </div>
        ))}
      </div>
      <div>
        <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-muted)' }}>Entity</div>
        {entityShapes.map((e) => (
          <div key={e.label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ fontSize: 11 }}>{e.shape}</span>
            {e.label}
          </div>
        ))}
      </div>
      {topRisk && (
        <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-muted)' }}>Highest Risk</div>
          <div style={{ color: 'var(--risk-high)', fontWeight: 600 }}>{topRisk.entity_id}</div>
          <div style={{ color: 'var(--text-muted)' }}>{topRisk.risk_score.toFixed(1)} / 100</div>
        </div>
      )}
    </div>
  );
}
