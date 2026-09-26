import { useEffect, useState } from 'react';
import { api } from '../api';

const STATUS_CONFIG = {
  verified: { label: 'Verified', className: 'status-ok' },
  clear: { label: 'Clear', className: 'status-ok' },
  review: { label: 'Review Required', className: 'status-warn' },
  escalate: { label: 'Escalate', className: 'status-danger' },
};

function StatusPill({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status, className: '' };
  return <span className={`req-status ${cfg.className}`}>{cfg.label}</span>;
}

function EvidenceChecklist({ checks }) {
  if (!checks?.length) return null;
  return (
    <div className="evidence-checks">
      {checks.map((c, i) => (
        <div key={i} className={`check-row ${c.match ? 'match' : 'no-match'}`}>
          <span className="check-icon">{c.match ? '✓' : '—'}</span>
          <div className="check-body">
            <div className="check-label">{c.label}</div>
            <div className="check-detail">{c.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function DuplicateComparison({ comp }) {
  if (!comp || comp.type !== 'duplicate') return null;
  const { invoice_a: a, invoice_b: b } = comp;
  return (
    <div className="comparison">
      <div className="comp-header">
        <div className="comp-label">Side-by-side comparison</div>
        <div className="comp-summary">
          {comp.shipments} shipment · {comp.total_financing} total financing · <b className="comp-exposure">{comp.exposure} at risk</b>
        </div>
      </div>
      <div className="comp-grid">
        <div className="comp-col">
          <div className="comp-tag">Submission A</div>
          <div className="comp-ref">{a.reference}</div>
          <div className="comp-kv">
            <div><span>Financier</span>{a.financier}</div>
            <div><span>Amount</span>{a.amount}</div>
            <div><span>Date</span>{a.date}</div>
            <div><span>Funded</span>{a.funded} · {a.fund_date}</div>
            <div><span>Repayment</span><span className={a.buyer_repaid ? 'repaid' : 'unpaid'}>{a.repaid_label}</span></div>
          </div>
        </div>
        <div className="comp-divider">
          <div className="comp-vs">VS</div>
        </div>
        <div className="comp-col comp-col-b">
          <div className="comp-tag comp-tag-b">Submission B</div>
          <div className="comp-ref">{b.reference}</div>
          <div className="comp-kv">
            <div><span>Financier</span>{b.financier}</div>
            <div><span>Amount</span>{b.amount}</div>
            <div><span>Date</span>{b.date}</div>
            <div><span>Funded</span>{b.funded} · {b.fund_date}</div>
            <div><span>Repayment</span><span className={b.buyer_repaid ? 'repaid' : 'unpaid'}>{b.repaid_label}</span></div>
          </div>
        </div>
      </div>
      <div className="comp-buyer">
        Buyer: <b>{comp.buyer}</b> · {comp.shipments} shipment for {comp.goods_value}
      </div>
    </div>
  );
}

function LoopComparison({ comp }) {
  if (!comp || comp.type !== 'loop') return null;
  return (
    <div className="comparison loop-comparison">
      <div className="comp-header">
        <div className="comp-label">Trading loop detail</div>
      </div>
      <div className="loop-route">
        {comp.route.map((r, i) => (
          <span key={r.id}>
            {i > 0 && <span className="loop-arrow">→</span>}
            <span className="loop-member">{r.name}</span>
          </span>
        ))}
        <span className="loop-arrow">→</span>
        <span className="loop-member">{comp.route[0]?.name}</span>
      </div>
      <div className="loop-stats">
        <div><span>Members</span><b>{comp.members}</b></div>
        <div><span>Rounds</span><b>{comp.rounds}</b></div>
        <div><span>Value cycled</span><b>{comp.value_cycled}</b></div>
        <div><span>Outside sales</span><b>{comp.outside_sales}</b></div>
      </div>
    </div>
  );
}

export default function RequestsView({ queue, caseId, onInvestigate }) {
  const [selected, setSelected] = useState(caseId);
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState(null);
  const choices = queue ? [...queue.alerts, ...queue.monitored.slice(0, 1)] : [];

  // Sync selected when caseId prop changes or pick first available
  useEffect(() => {
    if (caseId) {
      setSelected(caseId);
    } else if (!selected && choices.length > 0) {
      setSelected(choices[0].id);
    }
  }, [caseId, choices.length]);

  useEffect(() => {
    if (!selected) return;
    let live = true;
    setData(null);
    setExpanded(false);
    setError(null);
    api.tradeRequest(selected)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [selected]);

  if (!data) {
    return (
      <div className="requests-view">
        <div className="empty">{error || 'Loading trade request…'}</div>
      </div>
    );
  }

  const { trade: t, company: co, status: st, alert, evidence_checks: checks, comparison: comp } = data;
  const c = data.case;

  return (
    <div className="requests-view">
      <div className="req-head">
        <div>
          <div className="title serif">Trade Finance Request</div>
          <div className="sub">Incoming financing request — review before disbursement</div>
        </div>
        <div className="picker">
          <span>Show request for</span>
          {choices.map((ch) => (
            <button key={ch.id} className={`pick${ch.id === selected ? ' on' : ''}`} onClick={() => setSelected(ch.id)}>
              {ch.name}
            </button>
          ))}
        </div>
      </div>

      <div className="req-body">
        {/* Left: Trade request card */}
        <div className="req-card">
          <div className="req-card-head">
            <div>
              <div className="req-company serif">{co.name}</div>
              <div className="req-loc">{co.location} · {co.business}</div>
            </div>
            <span className={`score ${c.band}`}>{Math.round(c.risk_score)}</span>
          </div>

          <div className="req-trade-grid">
            <div className="req-field">
              <span className="req-field-label">Invoice</span>
              <span className="req-field-value">{t.invoice}</span>
            </div>
            <div className="req-field">
              <span className="req-field-label">Buyer</span>
              <span className="req-field-value">{t.buyer}</span>
            </div>
            <div className="req-field">
              <span className="req-field-label">Invoice Value</span>
              <span className="req-field-value req-field-big">{t.amount}</span>
            </div>
            <div className="req-field">
              <span className="req-field-label">Financing Requested</span>
              <span className="req-field-value req-field-big">{t.financing_requested}</span>
            </div>
            <div className="req-field">
              <span className="req-field-label">Financier</span>
              <span className="req-field-value">{t.financier}</span>
            </div>
            <div className="req-field">
              <span className="req-field-label">Date</span>
              <span className="req-field-value">{t.date}</span>
            </div>
          </div>

          <div className="req-statuses">
            <div className="req-status-item">
              <span className="req-status-label">Trade</span>
              <StatusPill status={st.trade} />
            </div>
            <div className="req-status-item">
              <span className="req-status-label">Entity</span>
              <StatusPill status={st.entity} />
            </div>
            <div className="req-status-item">
              <span className="req-status-label">Risk</span>
              <StatusPill status={st.risk} />
            </div>
          </div>

          {alert.present && (
            <button className="req-alert" onClick={() => setExpanded(!expanded)}>
              <span className="req-alert-icon">⚠</span>
              <span className="req-alert-text">{alert.headline}</span>
              <span className="req-alert-arrow">{expanded ? '▾' : '▸'}</span>
            </button>
          )}

          {!alert.present && (
            <div className="req-clear-banner">
              <span className="req-clear-icon">✓</span>
              No risk signals detected. Standard processing.
            </div>
          )}

          <div className="req-company-summary">
            <div className="label">Company profile</div>
            <div className="req-profile-grid">
              <div><span>Declared volume</span>{co.declared_volume}/yr</div>
              <div><span>Total financed</span>{co.total_financed} ({co.financed_pct})</div>
              <div><span>Financiers</span>{co.financiers}</div>
              <div><span>Buyers</span>{co.buyers}</div>
              <div><span>Invoices</span>{co.invoices}</div>
            </div>
          </div>

          <button className="btn btn-dark req-investigate-btn" onClick={() => onInvestigate(selected)}>
            Investigate {co.name} →
          </button>
        </div>

        {/* Right: Alert detail (expanded) */}
        {expanded && alert.present && (
          <div className="req-detail">
            <div className="req-detail-head">
              <div className="req-detail-title">Why this trade is flagged</div>
              <div className="req-detail-typology">
                {alert.typology === 'duplicate_financing' ? '🔴 Potential Duplicate Financing' : '🟠 Circular Trade Pattern'}
              </div>
            </div>

            <div className="req-detail-exposure">
              <span>Exposure potentially affected</span>
              <b>{alert.exposure}</b>
            </div>

            <EvidenceChecklist checks={checks} />

            {comp?.type === 'duplicate' && <DuplicateComparison comp={comp} />}
            {comp?.type === 'loop' && <LoopComparison comp={comp} />}

            <button className="btn btn-dark" style={{ alignSelf: 'flex-start', marginTop: 8 }} onClick={() => onInvestigate(selected)}>
              Start full investigation →
            </button>
          </div>
        )}

        {/* Right: Clean state */}
        {!alert.present && (
          <div className="req-detail req-detail-clean">
            <div className="req-detail-title">All checks passed</div>
            <div className="req-clean-body">
              <p>The financing request has been automatically screened against:</p>
              <ul>
                <li>Cross-financier duplicate invoice check</li>
                <li>Circular trade pattern detection</li>
                <li>Counterparty concentration analysis</li>
                <li>Volume vs. declared profile</li>
                <li>Behavioural anomaly signals</li>
              </ul>
              <p>No fraud patterns found. Weak signals only: <b>{c.headline}</b></p>
            </div>
            <button className="btn btn-dark" style={{ alignSelf: 'flex-start' }} onClick={() => onInvestigate(selected)}>
              View full investigation →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
