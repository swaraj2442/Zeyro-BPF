import { useEffect, useRef, useState } from 'react';
import { marked } from 'marked';

const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const md = (text) => marked.parse(escapeHtml(text || ''));

function sourceLabel(m) {
  if (m.source === 'live') return `Live · ${m.model}${m.cached ? ' · cached' : ''}`;
  return 'Offline · written from the computed findings, model unreachable';
}

function Message({ m }) {
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
                    <td key={j} className={j === r.cells.length - 1 ? 'num' : ''}>
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
  if (m.type === 'note') return <div className="msg" style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{m.text}</div>;
  return null;
}

export default function ChatPanel({
  caseInfo, stepIdx, steps, messages, busy, suggestions, isLast, verdictGiven, onSend, onNext, onVerdict,
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
          <Message key={m.id} m={m} />
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
