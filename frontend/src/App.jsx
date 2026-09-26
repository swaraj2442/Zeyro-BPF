import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api';
import CaseQueue from './components/CaseQueue';
import CaseGraph, { TYPE_LABEL } from './components/CaseGraph';
import ChatPanel from './components/ChatPanel';
import InputsView from './components/InputsView';

const SUGGESTIONS = {
  profile: (band) => [band === 'LOW' ? 'Why is this company not flagged?' : 'Why was this company flagged?'],
  financing: () => ['Is this financing pattern normal?'],
  duplicates: () => ["How do you know it's the same invoice?", 'Could this be legitimate refinancing?'],
  loop: () => ['Why does a closed loop matter?'],
  buyer: () => ['Who loses money here?'],
  verdict: () => ['What should I do first?', 'Who needs to be told?'],
};

const VERDICT_TEXT = { confirm: 'Confirmed as fraud', escalate: 'Escalated to the fraud team', dismiss: 'Cleared: no fraud' };

export default function App() {
  const [queue, setQueue] = useState(null);
  const [health, setHealth] = useState(null);
  const [feedback, setFeedback] = useState({});
  const [activeId, setActiveId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [stepIdx, setStepIdx] = useState(0);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [tempHighlight, setTempHighlight] = useState(null);
  const [error, setError] = useState(null);
  const [view, setView] = useState('investigate');
  const idRef = useRef(0);
  const runRef = useRef(0);
  const outputsShownRef = useRef(-1);

  const push = useCallback((...msgs) => {
    setMessages((prev) => [...prev, ...msgs.map((m) => ({ ...m, id: ++idRef.current }))]);
  }, []);

  const agentMsg = (res) => ({ type: 'agent', text: res.reply, source: res.source, model: res.model, cached: res.cached });

  const narrate = useCallback(async (caseId, i) => {
    const run = runRef.current;
    setBusy(true);
    try {
      const res = await api.narrate(caseId, i);
      if (runRef.current !== run) return;
      push(agentMsg(res));
    } catch (e) {
      if (runRef.current === run) push({ type: 'note', text: `Couldn't narrate this step: ${e.message}` });
    } finally {
      if (runRef.current === run) setBusy(false);
    }
  }, [push]);

  const openCase = useCallback(async (id) => {
    const run = ++runRef.current;
    setActiveId(id);
    setMessages([]);
    setTempHighlight(null);
    setBusy(true);
    try {
      const d = await api.caseDetail(id);
      if (runRef.current !== run) return;
      setDetail(d);
      setStepIdx(0);
      push({ type: 'step', index: 0, title: d.steps[0].title });
      await narrate(id, 0);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }, [narrate, push]);

  const loadAll = useCallback(async () => {
    try {
      const [q, h, f] = await Promise.all([api.cases(), api.health(), api.feedbackMap()]);
      setQueue(q);
      setHealth(h);
      setFeedback(f);
      setError(null);
      if (q.alerts[0]) openCase(q.alerts[0].id);
    } catch {
      setError('Cannot reach the Trade Sentinel API at localhost:8000. Is `uvicorn api:app` running?');
    }
  }, [openCase]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const steps = detail?.steps || [];
  const isLast = steps.length > 0 && stepIdx === steps.length - 1;

  useEffect(() => {
    if (!detail || busy || !isLast || outputsShownRef.current === runRef.current) return;
    outputsShownRef.current = runRef.current;
    push({ type: 'outputs', outputs: detail.outputs });
  }, [detail, busy, isLast, push]);

  const handleDraft = async (index, owner) => {
    const caseId = activeId;
    const run = runRef.current;
    setBusy(true);
    try {
      const res = await api.notice(caseId, index);
      if (runRef.current !== run) return;
      push({ type: 'notice', to: owner, text: res.reply, source: res.source, model: res.model, cached: res.cached });
    } catch (e) {
      push({ type: 'note', text: `Couldn't draft the notice: ${e.message}` });
    } finally {
      if (runRef.current === run) setBusy(false);
    }
  };

  const goTo = (target) => {
    const markers = [];
    for (let k = stepIdx + 1; k <= target; k++) markers.push({ type: 'step', index: k, title: steps[k].title });
    push(...markers);
    setStepIdx(target);
    setTempHighlight(null);
  };

  const handleNext = () => {
    if (busy || isLast) return;
    goTo(stepIdx + 1);
    narrate(activeId, stepIdx + 1);
  };

  const handleSend = async (text) => {
    const caseId = activeId;
    const run = runRef.current;
    const history = messages
      .filter((m) => m.type === 'user' || m.type === 'agent')
      .map((m) => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text }));
    push({ type: 'user', text });
    setBusy(true);
    try {
      const res = await api.ask(caseId, stepIdx, text, history);
      if (runRef.current !== run) return;
      if (res.step > stepIdx) goTo(res.step);
      push(agentMsg(res));
    } catch (e) {
      push({ type: 'note', text: `Couldn't answer: ${e.message}` });
    } finally {
      if (runRef.current === run) setBusy(false);
    }
  };

  const handleVerdict = async (verdict) => {
    await api.feedback(activeId, verdict);
    setFeedback((f) => ({ ...f, [activeId]: verdict }));
    push(
      { type: 'user', text: VERDICT_TEXT[verdict] },
      { type: 'note', text: 'Recorded. The agent shows this decision on future cases with the same fraud pattern.' }
    );
  };

  const nameOf = (id) => detail?.graph.nodes.find((n) => n.id === id)?.name || id;
  const flaggedRefs = new Set(
    (detail?.graph.edges || []).flatMap((e) => e.txns.filter((t) => t.flagged).map((t) => t.invoice))
  );

  const handleNodeClick = async (node) => {
    if (!node || !detail || busy) return;
    if (node.type === 'exporter' && node.id !== activeId) {
      openCase(node.id);
      return;
    }
    const linking = detail.graph.edges
      .filter((e) => [e.source, e.target].includes(node.id) && [e.source, e.target].includes(activeId))
      .map((e) => e.id);
    setTempHighlight({ nodes: [node.id, activeId], edges: linking });
    if (node.id === activeId) {
      const c = detail.case;
      push({
        type: 'card',
        card: {
          kicker: 'Company clicked',
          title: `${c.name} · risk ${c.risk_score}/100`,
          facts: [c.headline, ...(c.location ? [`${c.location} · ${c.business}`] : []), ...(c.patterns.length ? [`Signals: ${c.patterns.join(', ')}`] : [])],
        },
      });
      return;
    }
    try {
      const ctx = await api.context(node.id, activeId);
      push({
        type: 'card',
        card: {
          kicker: `${TYPE_LABEL[ctx.type] || ctx.type} clicked · its side of this case`,
          title: `${ctx.name}${ctx.location ? ` · ${ctx.location}` : ''}`,
          facts: ctx.facts,
          rows: ctx.transactions_with_case.map((t) => ({
            cells: [t.date, t.what, t.invoice, t.amount],
            flagged: flaggedRefs.has(t.invoice),
          })),
        },
      });
    } catch (e) {
      push({ type: 'note', text: `Couldn't load details: ${e.message}` });
    }
  };

  const handleEdgeClick = (edge) => {
    if (!edge || busy) return;
    setTempHighlight({ nodes: [edge.source, edge.target], edges: [edge.id] });
    push({
      type: 'card',
      card: {
        kicker: 'Line clicked · the transactions behind it',
        title: `${nameOf(edge.source)} → ${nameOf(edge.target)}: ${edge.label}`,
        facts: [`${edge.count} transaction${edge.count === 1 ? '' : 's'}, $${Math.round(edge.total).toLocaleString()} in total`],
        rows: edge.txns.slice(-8).map((t) => ({
          cells: [t.date, t.invoice, `$${Math.round(t.amount).toLocaleString()}`],
          flagged: t.flagged,
        })),
      },
    });
  };

  const handleReset = async () => {
    await api.reset();
    setFeedback({});
    loadAll();
  };

  const highlight = tempHighlight || steps[stepIdx]?.highlight || { nodes: [], edges: [] };
  const c = detail?.case;
  const suggestions = steps[stepIdx] ? SUGGESTIONS[steps[stepIdx].key](c?.band) : [];

  return (
    <div className="app">
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div className="wordmark serif">
            Zeyro <span>Trade Sentinel</span>
          </div>
          <span className="chip">Synthetic data only</span>
        </div>
        <div className="switch">
          <button className={view === 'investigate' ? 'on' : ''} onClick={() => setView('investigate')}>Investigations</button>
          <button className={view === 'inputs' ? 'on' : ''} onClick={() => setView('inputs')}>Inputs</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {health && (
            <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
              {health.entities} companies · {health.transactions} transactions scored
            </span>
          )}
          <button className="btn" onClick={handleReset}>Reset demo</button>
        </div>
      </header>

      {error ? (
        <div className="empty">{error}</div>
      ) : view === 'inputs' ? (
        <InputsView
          queue={queue}
          caseId={activeId}
          onInvestigate={(id) => {
            setView('investigate');
            if (id !== activeId) openCase(id);
          }}
        />
      ) : (
        <div className="body">
          <CaseQueue queue={queue} activeId={activeId} feedback={feedback} onOpen={openCase} />

          <main className="graph-pane">
            {c && (
              <div className="graph-head">
                <div className="title serif">{c.name}</div>
                <div className="sub">
                  {c.location ? `${c.location} · ${c.business} · ` : ''}risk {c.risk_score}/100 · {c.headline}
                </div>
                <div className="hints">
                  <span className="chip">Click a company → open its case</span>
                  <span className="chip">Click a financier, buyer or bank → their side of the story</span>
                  <span className="chip">Click a line → the invoices behind it</span>
                </div>
              </div>
            )}
            {detail ? (
              <CaseGraph
                graph={detail.graph}
                highlight={highlight}
                onNodeClick={handleNodeClick}
                onEdgeClick={handleEdgeClick}
                onBackgroundClick={() => setTempHighlight(null)}
              />
            ) : (
              <div className="empty">Loading case…</div>
            )}
            <div className="graph-legend">
              <span><i style={{ borderColor: '#1c1b19' }} />goods invoiced</span>
              <span><i style={{ borderColor: '#8a8578', borderTopStyle: 'dashed' }} />financing</span>
              <span><i style={{ borderColor: '#7fa876' }} />buyer payment</span>
              <span><i style={{ borderColor: '#c1543f', borderTopWidth: 3 }} />flagged in this step</span>
            </div>
          </main>

          <ChatPanel
            caseInfo={c}
            stepIdx={stepIdx}
            steps={steps}
            messages={messages}
            busy={busy}
            suggestions={suggestions}
            isLast={isLast}
            verdictGiven={Boolean(feedback[activeId])}
            onSend={handleSend}
            onNext={handleNext}
            onVerdict={handleVerdict}
            onDraft={handleDraft}
          />
        </div>
      )}
    </div>
  );
}
