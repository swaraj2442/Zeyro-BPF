import { buildInvestigationNote } from '../investigationNote';

const workflowTabs = ['Counterparty', 'Transaction', 'Early Warning', 'Investigation'];

function riskDotColor(score) {
  if (score > 70) return 'var(--risk-high)';
  if (score > 40) return 'var(--risk-med)';
  return 'var(--risk-low)';
}

function NoteBlock({ line }) {
  if (line.type === 'header') {
    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 600 }}>{line.text}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{line.sub}</div>
      </div>
    );
  }
  if (line.type === 'body') {
    return <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6, marginBottom: 12 }}>{line.text}</div>;
  }
  if (line.type === 'section') {
    return (
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
          {line.title}
        </div>
        {line.text && <div style={{ fontSize: 13, lineHeight: 1.6 }}>{line.text}</div>}
        {line.list && (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {line.list.map((item, i) => (
              <li key={i} style={{ fontSize: 13, lineHeight: 1.7 }}>{item}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  if (line.type === 'footer') {
    return (
      <div
        style={{
          marginTop: 16,
          padding: '10px 14px',
          background: 'var(--surface-muted)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        {line.text}
      </div>
    );
  }
  return null;
}

export default function SidePanel({ entity, activeWorkflow, onWorkflowChange }) {
  return (
    <div
      style={{
        width: 380,
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', padding: '10px 12px', gap: 4, overflowX: 'auto' }}>
        {workflowTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => onWorkflowChange(tab)}
            style={{
              padding: '6px 12px',
              borderRadius: 999,
              border: 'none',
              background: activeWorkflow === tab ? 'var(--surface-muted)' : 'transparent',
              color: activeWorkflow === tab ? 'var(--text)' : 'var(--text-faint)',
              fontSize: 12,
              fontWeight: 500,
              whiteSpace: 'nowrap',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {!entity ? (
          <div style={{ color: 'var(--text-faint)', fontSize: 13, textAlign: 'center', marginTop: 60 }}>
            Select an entity on the graph to view its Trade Sentinel investigation note.
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: riskDotColor(entity.risk_score),
                  display: 'inline-block',
                }}
              />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>
                Trade Sentinel Agent
              </span>
            </div>
            <div
              style={{
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: 18,
              }}
            >
              {buildInvestigationNote(entity).map((line, i) => (
                <NoteBlock key={i} line={line} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
