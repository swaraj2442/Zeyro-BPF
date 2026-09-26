const tabs = ['Overview', 'Network', 'Transactions', 'Alerts'];

export default function TopNav({ activeTab, onTabChange, onRegenerate, entityCount, txCount }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 24px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className="serif" style={{ fontSize: 22, letterSpacing: 0.2 }}>
          Zeyro <span style={{ color: 'var(--text-muted)' }}>Trade Sentinel</span>
        </span>
      </div>

      <div style={{ display: 'flex', gap: 4, background: 'var(--surface-muted)', padding: 4, borderRadius: 999 }}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            style={{
              padding: '6px 16px',
              borderRadius: 999,
              border: 'none',
              background: activeTab === tab ? 'var(--accent)' : 'transparent',
              color: activeTab === tab ? 'var(--accent-text)' : 'var(--text-muted)',
              fontSize: 13,
              fontWeight: 500,
              transition: 'all 0.15s',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {entityCount} entities · {txCount} transactions
        </span>
        <button
          onClick={onRegenerate}
          style={{
            padding: '8px 18px',
            borderRadius: 999,
            border: 'none',
            background: 'var(--accent)',
            color: 'var(--accent-text)',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Regenerate Dataset
        </button>
      </div>
    </div>
  );
}
