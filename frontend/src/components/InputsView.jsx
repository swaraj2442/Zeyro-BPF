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

export default function InputsView({ queue, caseId, onInvestigate }) {
  const [selected, setSelected] = useState(caseId);
  const [trace, setTrace] = useState(null);
  const choices = queue ? [...queue.alerts, ...queue.monitored.slice(0, 1)] : [];
  const patterns = trace?.case.patterns || [];
  const entryStage = patterns.includes('Same invoice financed twice')
    ? 'financing_request'
    : patterns.includes('Goods moving in a closed loop')
      ? 'sale'
      : null;

  useEffect(() => {
    if (!selected) return;
    let live = true;
    setTrace(null);
    api.inputs(selected).then((t) => live && setTrace(t));
    return () => {
      live = false;
    };
  }, [selected]);

  return (
    <div className="inputs">
      <div className="inputs-head">
        <div>
          <div className="title serif">Where the data comes from</div>
          <div className="sub">
            One cross-border invoice on a trade-finance marketplace (modelled on RXIL Global's ITFS flow), left to right.
            Each step shows what Trade Sentinel reads and which investigation check uses it.
          </div>
        </div>
        <div className="picker">
          <span>Show real records for</span>
          {choices.map((c) => (
            <button key={c.id} className={`pick${c.id === selected ? ' on' : ''}`} onClick={() => setSelected(c.id)}>
              {c.name}
            </button>
          ))}
        </div>
      </div>

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
                {s.fields.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              {s.docs && <div className="docs">{s.docs}</div>}
              <div className="label">{trace ? trace.case.name : 'This case'}</div>
              <div className="stage-body">
                <StageBody stage={s} trace={trace} />
              </div>
              <div className="feeds">
                {s.feeds.map((f) => (
                  <span key={f} className={`feed${s.status === 'planned' ? ' planned' : ''}`}>→ {f}</span>
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
    </div>
  );
}
