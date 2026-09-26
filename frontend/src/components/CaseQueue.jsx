const STATUS = { confirm: 'Confirmed fraud', dismiss: 'Cleared', escalate: 'Escalated' };

function CaseCard({ c, active, status, onOpen }) {
  return (
    <button className={`case-card${active ? ' active' : ''}`} onClick={() => onOpen(c.id)}>
      <div className="row">
        <div className="name">{c.name}</div>
        <span className={`score ${c.band}`}>{Math.round(c.risk_score)}</span>
      </div>
      <div className="loc">{c.location ? `${c.location} · ${c.business}` : 'Background company'}</div>
      <div className="headline">{c.headline}</div>
      {c.linked && <div className="linked">+ linked: {c.linked.join(', ')}</div>}
      {status && <div className="status">Analyst: {STATUS[status]}</div>}
    </button>
  );
}

export default function CaseQueue({ queue, activeId, feedback, onOpen }) {
  if (!queue) return <aside className="queue" />;
  return (
    <aside className="queue">
      <h4>Needs review · {queue.alerts.length}</h4>
      {queue.alerts.map((c) => (
        <CaseCard key={c.id} c={c} active={c.id === activeId} status={feedback[c.id]} onOpen={onOpen} />
      ))}
      <h4 style={{ marginTop: 22 }}>Largest exporters · no alerts</h4>
      {queue.monitored.map((c) => (
        <CaseCard key={c.id} c={c} active={c.id === activeId} status={feedback[c.id]} onOpen={onOpen} />
      ))}
      <div style={{ fontSize: 11.5, color: 'var(--text-faint)', margin: '14px 6px 0', lineHeight: 1.5 }}>
        {queue.total_exporters} exporters scored on every load. All companies and trades are synthetic.
      </div>
    </aside>
  );
}
