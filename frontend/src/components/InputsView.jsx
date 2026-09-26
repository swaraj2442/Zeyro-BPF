import { useEffect, useState } from 'react';
import { api } from '../api';

const STAGES = [
  {
    key: 'onboarding', title: 'Onboarding', sub: 'KYC · KYB · AML', who: 'Marketplace onboards both parties',
    fields: ['Legal name & entity type', 'Country and city', 'Line of business', 'Declared annual turnover'],
    feeds: ['Review the company', 'Volume vs declared'], status: 'used',
  },
  {
    key: 'limits', title: 'Limits', sub: 'Exposure per importer', who: 'Financier sets on the platform',
    fields: ['Limit amount and currency', 'With cover / without cover', 'Min–max spread'],
    feeds: ['Limit utilisation'], status: 'planned',
  },
  {
    key: 'sale', title: 'Invoice upload', sub: 'Trade factoring unit', who: 'Exporter or importer, manual upload',
    fields: ['Invoice no., buyer, amount, date', 'Importer accepts the invoice'],
    docs: 'Documents (PO, bill of lading, packing list, certificate of origin) not used yet',
    feeds: ['Where the goods went', 'Sale behind each financing'], status: 'used',
  },
  {
    key: 'financing_request', title: 'Bids & financing', sub: 'A financier wins the invoice', who: 'Financiers bid within their limits',
    fields: ['Invoice no. as financed', 'Winning financier', 'Amount and date'],
    feeds: ['Invoices financed twice'], status: 'used',
  },
  {
    key: 'funding', title: 'Funding', sub: 'Accepted bid is settled', who: 'Financier pays the exporter',
    fields: ['Amount paid after discount', 'Date paid'],
    feeds: ['Money at risk'], status: 'used',
  },
  {
    key: 'settlement', title: 'Repayment', sub: 'At invoice maturity', who: 'Buyer pays the financier',
    fields: ['Payer and payee', 'Amount and date'],
    feeds: ['What the buyer paid'], status: 'used',
  },
];

const PLUG_IN = [
  { step: 'Review the company', from: [1] },
  { step: 'Financing history', from: [4] },
  { step: 'Invoices financed twice', from: [4, 5] },
  { step: 'Where the goods went', from: [3] },
  { step: 'What the buyer paid', from: [3, 6] },
  { step: 'Verdict', from: [1, 3, 4, 5, 6] },
];

function Record({ r }) {
  return (
    <div className={`rec${r.flagged ? ' flagged' : ''}`}>
      <div className="rec-top">
        <span className="rec-inv">{r.invoice}</span>
        <span>{r.amount}</span>
      </div>
      <div className="rec-sub">
        {r.from} → {r.to} · {r.date}
      </div>
    </div>
  );
}

function StageBody({ stage, trace }) {
  if (!trace) return <div className="stage-empty">Loading…</div>;
  if (stage.key === 'onboarding') {
    const o = trace.onboarding;
    return (
      <div className="kv">
        <div><span>Name</span>{o.legal_name}</div>
        <div><span>Type</span>{o.entity_type}</div>
        <div><span>Location</span>{o.location}</div>
        <div><span>Business</span>{o.line_of_business}</div>
        <div><span>Declared</span>{o.declared_annual_turnover} / yr</div>
      </div>
    );
  }
  if (stage.key === 'limits') {
    return <div className="stage-empty">Not in the demo dataset. Next: compare financing against each importer's limit.</div>;
  }
  const rec = trace.records[stage.key];
  return (
    <>
      <div className="rec-count">{rec.count} record{rec.count === 1 ? '' : 's'}</div>
      {rec.examples.slice(0, 2).map((r, i) => (
        <Record key={i} r={r} />
      ))}
    </>
  );
}

function SourceItem({ icon, title, count, status }) {
  const isReview = status === 'REVIEW';
  return (
    <div className="src-item">
      <div className="src-left">
        <span className="src-icon">{icon}</span>
        <span className="src-title">{title}</span>
      </div>
      <div className="src-right">
        <span className="src-count">{count} signals</span>
        <span className={`src-status ${isReview ? 'review' : 'verified'}`}>
          {isReview ? '⚠ REVIEW' : '● VERIFIED'}
        </span>
      </div>
    </div>
  );
}

function DrilldownPanel({ title, children }) {
  return (
    <div className="dd-panel">
      <div className="dd-title">{title}</div>
      <div className="dd-body">{children}</div>
    </div>
  );
}

export default function InputsView({ queue, caseId, onInvestigate }) {
  const [selected, setSelected] = useState(caseId);
  const [trace, setTrace] = useState(null);
  const [showRaw, setShowRaw] = useState(false);
  
  const choices = queue ? [...queue.alerts, ...queue.monitored.slice(0, 1)] : [];
  const patterns = trace?.case.patterns || [];
  const entryStage = patterns.includes('Same invoice financed twice')
    ? 'financing_request'
    : patterns.includes('Goods moving in a closed loop')
      ? 'sale'
      : null;

  useEffect(() => {
    if (!selected && choices.length > 0) {
      setSelected(choices[0].id);
    }
  }, [selected, choices]);

  useEffect(() => {
    if (!selected) return;
    let live = true;
    setTrace(null);
    api.inputs(selected).then((t) => live && setTrace(t));
    return () => { live = false; };
  }, [selected]);

  if (!trace) {
    return (
      <div className="inputs empty">
        <div className="empty">Loading trade fingerprint…</div>
      </div>
    );
  }

  const { fingerprint, case: c } = trace;
  if (!fingerprint) return null;
  const f = fingerprint;

  const isReview = f.sources.financial.status === 'REVIEW';

  return (
    <div className={showRaw ? "inputs" : "fp-view"}>
      <div className={showRaw ? "inputs-head" : "fp-head"}>
        <div>
          <div className="title serif">{showRaw ? 'Where the data comes from' : 'Zeyro Digital Trade Fingerprint™'}</div>
          <div className="sub">
            {showRaw 
              ? 'One cross-border invoice on a trade-finance marketplace (modelled on RXIL Global\'s ITFS flow), left to right.'
              : 'A continuously generated, multi-source digital identity of a trade, combining entity, transaction, document, shipment, financing and behavioural signals into one explainable intelligence layer.'}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
          <button className="btn btn-outline" style={{ fontSize: '12px', padding: '4px 12px' }} onClick={() => setShowRaw(!showRaw)}>
            {showRaw ? '← Back to Fingerprint' : 'View Raw Data Flow →'}
          </button>
          <div className="picker">
            <span>Show records for</span>
            {choices.map((ch) => (
              <button key={ch.id} className={`pick${ch.id === selected ? ' on' : ''}`} onClick={() => setSelected(ch.id)}>
                {ch.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {showRaw ? (
        <>
          <div className="flow">
            {STAGES.map((s, i) => (
              <div key={s.key} className="flow-cell">
                <div className={`stage${s.status === 'planned' ? ' planned' : ''}${s.key === entryStage ? ' key' : ''}`}>
                  {s.key === entryStage && <div className="entry-tag">Fraud enters here</div>}
                  <div className="stage-head">
                    <span className="num">{i + 1}</span>
                    <div>
                      <div className="stage-title">{s.title}</div>
                      <div className="stage-sub">{s.sub}</div>
                    </div>
                    <span className={`status ${s.status}`}>{s.status === 'used' ? 'Used' : 'Not used yet'}</span>
                  </div>
                  <div className="who">{s.who}</div>
                  <div className="label">Data in</div>
                  <ul className="fields">
                    {s.fields.map((fld) => (
                      <li key={fld}>{fld}</li>
                    ))}
                  </ul>
                  {s.docs && <div className="docs">{s.docs}</div>}
                  <div className="label">{trace ? trace.case.name : 'This case'}</div>
                  <div className="stage-body">
                    <StageBody stage={s} trace={trace} />
                  </div>
                  <div className="feeds">
                    {s.feeds.map((feed) => (
                      <span key={feed} className={`feed${s.status === 'planned' ? ' planned' : ''}`}>→ {feed}</span>
                    ))}
                  </div>
                </div>
                {i < STAGES.length - 1 && <div className="arrow">›</div>}
              </div>
            ))}
          </div>

          <div className="inputs-foot">
            <div className="panel">
              <div className="label">Where Trade Sentinel plugs in: the investigation step and the inputs it reads</div>
              <div className="plug">
                {PLUG_IN.map((p) => (
                  <div key={p.step} className="plug-item">
                    <span>{p.step}</span>
                    <span className="plug-nums">
                      {p.from.map((n) => (
                        <b key={n}>{n}</b>
                      ))}
                    </span>
                  </div>
                ))}
              </div>
              <div className="integration">
                <b>How it arrives.</b> Today, invoices are uploaded manually on the marketplace, with no custom APIs (ITFS lists
                API/SFTP). Trade Sentinel needs the same four record types (invoice, financing, funding, repayment) from{' '}
                <b>every</b> marketplace, bank and factor, as a daily file or feed. The demo uses synthetic records in that shape.
              </div>
            </div>
            <div className="panel story">
              <div className="label">Why one marketplace alone misses it{trace ? ` · ${trace.case.name}` : ''}</div>
              <div className="story-text">{trace?.story}</div>
              {trace && (
                <button className="btn btn-dark" onClick={() => onInvestigate(trace.case.id)}>
                  Investigate {trace.case.name} →
                </button>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="fp-content">
          <div className="fp-hero-col">
            <div className="fp-hero">
              <div className="fp-hero-header">
                <span className="fp-breadcrumbs">← Digital Trade Consortium &nbsp;&nbsp;/&nbsp;&nbsp; {c.name}</span>
              </div>
              
              <div className="fp-card">
                <div className="fp-title">DIGITAL TRADE FINGERPRINT</div>
                <div className="fp-score-ring">
                  <div className={`fp-score ${isReview ? 'review' : 'trusted'}`}>{f.score}</div>
                  <div className="fp-score-label">{isReview ? 'REVIEW' : 'TRUSTED'}</div>
                  <div className="fp-score-max">/ 100</div>
                </div>

                <div className="fp-sources-list">
                  <div className="fp-sources-hdr">SOURCES</div>
                  <SourceItem icon="🏦" title="BANK" count={f.sources.bank.count} status={f.sources.bank.status} />
                  <SourceItem icon="🚢" title="TRADE" count={f.sources.trade.count} status={f.sources.trade.status} />
                  <SourceItem icon="🪪" title="IDENTITY" count={f.sources.identity.count} status={f.sources.identity.status} />
                  <SourceItem icon="📄" title="DOCUMENTS" count={f.sources.documents.count} status={f.sources.documents.status} />
                  <SourceItem icon="💳" title="FINANCIAL" count={f.sources.financial.count} status={f.sources.financial.status} />
                  <SourceItem icon="🕸" title="NETWORK" count={f.sources.network.count} status={f.sources.network.status} />
                </div>

                <div className="fp-freshness">
                  <div className="fp-sources-hdr">DATA FRESHNESS</div>
                  <div className="fresh-row"><span>Bank data</span><span>Today</span></div>
                  <div className="fresh-row"><span>Shipment</span><span>4 hrs ago</span></div>
                  <div className="fresh-row"><span>KYC</span><span>2 days ago</span></div>
                  <div className="fresh-row"><span>Entity data</span><span>1 day ago</span></div>
                </div>
              </div>
            </div>
          </div>

          <div className="fp-drilldowns">
            <div className="dd-grid">
              <DrilldownPanel title="IDENTITY">
                <div className="dd-main-val">{f.identity.legal_name}</div>
                <div className="kv-list mt-sm">
                  <div><span>Legal Entity</span><span className="v-ok">✓ {f.identity.kyb}</span></div>
                  <div><span>GSTIN</span><span className="v-ok">✓ {f.identity.gstin}</span></div>
                  <div><span>LEI</span><span className="v-ok">✓ {f.identity.lei}</span></div>
                  <div><span>UBO</span><span className="v-ok">✓ {f.identity.ubo}</span></div>
                </div>
                <div className="kv-list mt-sm pt-sm border-t">
                  <div><span>Related entities</span><span>{f.identity.related_entities}</span></div>
                  <div><span>Common directors</span><span>{f.identity.common_directors}</span></div>
                  <div><span>Jurisdictions</span><span>{f.identity.jurisdictions}</span></div>
                </div>
              </DrilldownPanel>

              <DrilldownPanel title="TRADE">
                <div className="kv-list">
                  <div><span>Invoice</span><span>{f.trade.invoice}</span></div>
                  <div><span>Invoice Value</span><span>{f.trade.invoice_value}</span></div>
                  <div><span>Buyer</span><span>{f.trade.buyer}</span></div>
                  <div><span>Goods</span><span>{f.trade.goods}</span></div>
                  <div><span>Origin</span><span>{f.trade.origin}</span></div>
                  <div><span>Destination</span><span>{f.trade.destination}</span></div>
                </div>
                <div className="kv-list mt-sm pt-sm border-t">
                  <div><span>Customs</span><span className="v-ok">✓ {f.trade.customs}</span></div>
                  <div><span>Shipment</span><span className={f.trade.shipment==='Matched'?'v-ok':'v-warn'}>{f.trade.shipment==='Matched'?'✓':'⚠'} {f.trade.shipment}</span></div>
                  <div><span>Bill of Lading</span><span className={f.trade.bill_of_lading==='Matched'?'v-ok':'v-warn'}>{f.trade.bill_of_lading==='Matched'?'✓':'⚠'} {f.trade.bill_of_lading}</span></div>
                </div>
                <div className="mt-sm pt-sm border-t flex-between">
                  <span>Trade consistency</span>
                  <span className={f.trade.consistency === '94%' ? 'text-green' : 'text-orange'}>{f.trade.consistency}</span>
                </div>
              </DrilldownPanel>

              <DrilldownPanel title="FINANCING">
                <div className="kv-list">
                  <div><span>Requested</span><span>{f.financing.requested}</span></div>
                  <div><span>Financier</span><span>{f.financing.financier}</span></div>
                  <div><span>Tenor</span><span>{f.financing.tenor}</span></div>
                </div>
                <div className="kv-list mt-sm pt-sm border-t">
                  <div><span>Existing exposure</span><span>{f.financing.existing_exposure}</span></div>
                  <div><span>Historical trades</span><span>{f.financing.historical_trades}</span></div>
                  <div><span>Average financing</span><span>{f.financing.avg_financing}</span></div>
                </div>
                {f.financing.overlap_detected && (
                  <div className="overlap-alert mt-sm">
                    <div className="overlap-hdr">⚠ POTENTIAL OVERLAP DETECTED</div>
                    <ul className="overlap-evidence">
                      {f.financing.evidence.map(ev => <li key={ev}>{ev}</li>)}
                    </ul>
                    <button className="btn btn-dark w-full mt-sm" onClick={() => onInvestigate(c.id)}>
                      Investigate →
                    </button>
                  </div>
                )}
              </DrilldownPanel>

              <DrilldownPanel title="NETWORK">
                <div className="network-vis">
                  <div className="nv-buyer">{f.network.buyer}</div>
                  <div className="nv-edge-down">
                    <div className="nv-val">{f.network.trade_value} Trade</div>
                  </div>
                  <div className="nv-exporter">{f.network.exporter}</div>
                  
                  <div className="nv-tree">
                    <div className="nv-tree-stem"></div>
                    <div className="nv-tree-branches">
                      <div className="nv-branch">
                        <div className="nv-node">UBO</div>
                      </div>
                      <div className="nv-branch">
                        <div className="nv-node">{f.network.financier}</div>
                        <div className="nv-label">Financing</div>
                      </div>
                      <div className="nv-branch">
                        <div className="nv-node">COMPANY X</div>
                        <div className="nv-label">Common UBO</div>
                      </div>
                    </div>
                  </div>
                </div>
              </DrilldownPanel>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
