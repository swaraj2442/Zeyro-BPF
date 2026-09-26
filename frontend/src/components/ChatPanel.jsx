import { useEffect, useRef, useState } from 'react';
import { marked } from 'marked';

const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const md = (text, opts) => marked.parse(escapeHtml(text || ''), opts);

function sourceLabel(m) {
  if (m.source === 'live') return `Live · ${m.model}${m.cached ? ' · cached' : ''}`;
  return 'Offline · written from the computed findings, model unreachable';
}

function OutputsCard({ o, busy, onDraft }) {
  return (
    <div className="out">
      <div className="out-head">
        <span className="kicker">Trade Sentinel output · what the product hands to your team</span>
        <span className={`score ${o.band}`}>{Math.round(o.score)}</span>
      </div>
      <div className="out-decision">{o.decision}</div>
      <div className="out-risk">
        <div>
          <span>Money at risk</span>
          <b>{o.money_at_risk.amount}</b>
        </div>
        <div>
          <span>Held by</span>
          <b className="held">{o.money_at_risk.held_by}</b>
        </div>
        <div className="basis">{o.money_at_risk.basis}</div>
      </div>
      <div className="out-label">Actions, in order</div>
      <ol className="out-actions">
        {o.actions.map((a, i) => (
          <li key={i}>
            <div className="act-title">{a.action}</div>
            <div className="act-meta">
              <span className="owner">{a.owner}</span>
              <span className="when">{a.when}</span>
            </div>
            <div className="act-why">Why: {a.evidence}</div>
            {a.notice && (
              <button className="btn act-btn" disabled={busy} onClick={() => onDraft(i, a.owner)}>
                Draft notice to {a.owner} →
              </button>
            )}
          </li>
        ))}
      </ol>
      <div className="out-label">Monitoring rules created</div>
      <ul className="out-list">
        {o.watch.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      {o.evidence_categorized ? (
        <>
          <div className="out-label">Evidence pack</div>
          {Object.entries(o.evidence_categorized).map(([cat, items]) =>
            items.length > 0 && (
              <details key={cat} className="evidence-category" open>
                <summary>{cat} · {items.length}</summary>
                <ul className="out-list">
                  {items.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </details>
            )
          )}
        </>
      ) : (
        <details className="out-pack">
          <summary>Evidence pack · {o.evidence_pack.length} records</summary>
          <ul className="out-list">
            {o.evidence_pack.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function Message({ m, busy, onDraft }) {
  if (m.type === 'step') {
    return <div className="step-marker">Step {m.index + 1} · {m.title}</div>;
  }
  if (m.type === 'user') return <div className="msg user">{m.text}</div>;
  if (m.type === 'agent') {
    return (
      <div className="msg agent">
        <div dangerouslySetInnerHTML={{ __html: md(m.text) }} />
        <div className="meta">{sourceLabel(m)}</div>
      </div>
    );
  }
  if (m.type === 'card') {
    const c = m.card;
    return (
      <div className="card">
        <div className="kicker">{c.kicker}</div>
        <div className="card-title">{c.title}</div>
        {c.facts?.length > 0 && (
          <ul>
            {c.facts.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        )}
        {c.rows?.length > 0 && (
          <table>
            <tbody>
              {c.rows.map((r, i) => (
                <tr key={i} className={r.flagged ? 'flagged' : ''}>
                  {r.cells.map((cell, j) => (
                    <td key={j} className={j === r.cells.length - 1 ? 'amt' : ''}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );
  }
  if (m.type === 'outputs') return <OutputsCard o={m.outputs} busy={busy} onDraft={onDraft} />;
  if (m.type === 'notice') {
    return (
      <div className="card notice">
        <div className="kicker">Draft notice · to {m.to}</div>
        <div className="notice-body" dangerouslySetInnerHTML={{ __html: md(m.text, { breaks: true }) }} />
        <div className="meta">{sourceLabel(m)} · review before sending</div>
      </div>
    );
  }
  if (m.type === 'note') return <div className="msg" style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{m.text}</div>;
  return null;
}

export default function ChatPanel({
  caseInfo, stepIdx, steps, messages, busy, suggestions, isLast, verdictGiven, onSend, onNext, onVerdict, onDraft,
}) {
  const clean = caseInfo?.band === 'LOW';
  const [draft, setDraft] = useState('');
  const threadRef = useRef(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  const send = (text) => {
    const t = text.trim();
    if (!t || busy) return;
    setDraft('');
    onSend(t);
  };

  return (
    <section className="chat">
      <div className="chat-head">
        <div className="agent">
          <span className="agent-dot">TS</span> Trade Sentinel
          <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· AI investigator</span>
        </div>
        {caseInfo && steps.length > 0 && (
          <>
            <div className="progress">
              {steps.map((s, i) => (
                <div key={s.key} className={i <= stepIdx ? 'done' : ''} title={s.title} />
              ))}
            </div>
            <div className="progress-label">
              Step {stepIdx + 1} of {steps.length}: {steps[stepIdx]?.title}
            </div>
          </>
        )}
      </div>

      <div className="thread" ref={threadRef}>
        {!caseInfo && <div className="empty">Pick a case on the left and I'll investigate it step by step.</div>}
        {messages.map((m) => (
          <Message key={m.id} m={m} busy={busy} onDraft={onDraft} />
        ))}
        {busy && (
          <div className="typing">
            <span /><span /><span /> Investigating…
          </div>
        )}
      </div>

      {caseInfo && (
        <div className="composer">
          {isLast && !busy && !verdictGiven ? (
            <div className="actions" style={{ marginBottom: 10 }}>
              {clean ? (
                <>
                  <button className="btn btn-dark" onClick={() => onVerdict('dismiss')}>Agree: clear</button>
                  <button className="btn" onClick={() => onVerdict('escalate')}>Escalate anyway</button>
                </>
              ) : (
                <>
                  <button className="btn btn-danger" onClick={() => onVerdict('confirm')}>Confirm fraud</button>
                  <button className="btn btn-dark" onClick={() => onVerdict('escalate')}>Escalate</button>
                  <button className="btn" onClick={() => onVerdict('dismiss')}>Dismiss</button>
                </>
              )}
            </div>
          ) : (
            <div className="suggestions">
              {!isLast && (
                <button className="suggestion primary" disabled={busy} onClick={onNext}>
                  Next: {steps[stepIdx + 1]?.title} →
                </button>
              )}
              {suggestions.map((s) => (
                <button key={s} className="suggestion" disabled={busy} onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <form
            className="input-row"
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about this case, or say “next”"
              disabled={busy}
            />
            <button className="btn btn-dark" type="submit" disabled={busy || !draft.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
