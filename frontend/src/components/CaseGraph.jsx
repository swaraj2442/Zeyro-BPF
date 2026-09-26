import { useEffect, useRef } from 'react';
import { Network } from 'vis-network/standalone/esm/vis-network.mjs';
import { DataSet } from 'vis-data/standalone/esm/vis-data.mjs';

export const TYPE_LABEL = { exporter: 'Exporter', importer: 'Buyer', factor: 'Factor', bank: 'Bank' };

const CLICK_HINT = {
  exporter: 'open its case',
  importer: "see the buyer's side",
  factor: "see the financier's side",
  bank: "see the bank's side",
};

const EDGE_COLOR = { financing_request: '#8a8578', funding: '#b7b2a4', sale: '#1c1b19', settlement: '#7fa876' };
const FLAG = '#c1543f';

const esc = (s) => String(s).replace(/[<>]/g, '');

function nodeStyle(n, hl) {
  const dim = hl.nodes.length > 0 && !hl.nodes.includes(n.id);
  const lit = hl.nodes.includes(n.id) && !n.is_focus;
  let bg = '#ffffff';
  if (n.type === 'exporter' && n.risk_score > 70) bg = '#f6e3de';
  else if (n.type === 'exporter' && n.risk_score > 50) bg = '#f8eedc';
  return {
    id: n.id,
    label: `<b>${esc(n.name)}</b>\n${TYPE_LABEL[n.type] || n.type}${n.location ? ` · ${esc(n.location)}` : ''}`,
    title: `${n.name}\n${TYPE_LABEL[n.type] || n.type}${n.location ? ` · ${n.location}` : ''}\nRisk ${n.risk_score}/100\nClick to ${n.is_focus ? 'see its summary' : CLICK_HINT[n.type] || 'see details'}`,
    shape: 'box',
    margin: { top: 9, bottom: 9, left: 12, right: 12 },
    font: { multi: 'html', face: 'Inter', size: 13, color: '#1c1b19', bold: { face: 'Inter', size: 13 } },
    borderWidth: n.is_focus ? 2.5 : lit ? 2.5 : 1,
    color: {
      background: bg,
      border: lit ? FLAG : n.is_focus ? '#171614' : '#d9d3c7',
      highlight: { background: bg, border: '#171614' },
      hover: { background: bg, border: '#171614' },
    },
    shapeProperties: { borderRadius: 10 },
    opacity: dim ? 0.3 : 1,
  };
}

function edgeStyle(e, hl) {
  const lit = hl.edges.includes(e.id);
  const dim = hl.edges.length > 0 && !lit;
  const base = EDGE_COLOR[e.kind] || '#b7b2a4';
  return {
    id: e.id,
    from: e.source,
    to: e.target,
    arrows: { to: { enabled: true, scaleFactor: 0.5 } },
    dashes: e.kind === 'financing_request' || e.kind === 'funding',
    width: lit ? 3 : 1.2,
    color: { color: lit ? FLAG : base, opacity: dim ? 0.15 : 0.85, highlight: '#171614', hover: '#171614' },
    label: `${e.label} ×${e.count}`,
    font: lit
      ? { size: 11, face: 'Inter', color: FLAG, strokeWidth: 4, strokeColor: '#f6f3ee', align: 'middle' }
      : { size: 11, face: 'Inter', color: 'rgba(0,0,0,0)', strokeWidth: 0, align: 'middle' },
    smooth: { type: 'curvedCW', roundness: 0.18 },
    title: `${e.label} ×${e.count} · $${Math.round(e.total).toLocaleString()}\nClick to see the invoices`,
  };
}

export default function CaseGraph({ graph, highlight, onNodeClick, onEdgeClick, onBackgroundClick }) {
  const containerRef = useRef(null);
  const netRef = useRef(null);
  const dataRef = useRef(null);
  const handlers = useRef({});
  handlers.current = { onNodeClick, onEdgeClick, onBackgroundClick };

  useEffect(() => {
    if (!containerRef.current || !graph) return;
    const hl = highlight || { nodes: [], edges: [] };
    const nodes = new DataSet(graph.nodes.map((n) => nodeStyle(n, hl)));
    const edges = new DataSet(graph.edges.map((e) => edgeStyle(e, hl)));
    dataRef.current = { nodes, edges };

    const network = new Network(
      containerRef.current,
      { nodes, edges },
      {
        physics: {
          solver: 'barnesHut',
          barnesHut: { gravitationalConstant: -9000, springLength: 190, springConstant: 0.03, avoidOverlap: 1 },
          stabilization: { iterations: 400, fit: true },
        },
        interaction: { hover: true, tooltipDelay: 150 },
      }
    );
    network.once('stabilizationIterationsDone', () => {
      network.setOptions({ physics: false });
      network.fit({ animation: false });
    });
    network.on('click', (params) => {
      const h = handlers.current;
      if (params.nodes.length) h.onNodeClick(graph.nodes.find((n) => n.id === params.nodes[0]));
      else if (params.edges.length) h.onEdgeClick(graph.edges.find((e) => e.id === params.edges[0]));
      else h.onBackgroundClick();
    });
    network.on('hoverNode', () => (containerRef.current.style.cursor = 'pointer'));
    network.on('hoverEdge', () => (containerRef.current.style.cursor = 'pointer'));
    network.on('blurNode', () => (containerRef.current.style.cursor = 'default'));
    network.on('blurEdge', () => (containerRef.current.style.cursor = 'default'));
    netRef.current = network;
    if (import.meta.env.DEV) window.__caseNetwork = network;
    return () => network.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  useEffect(() => {
    if (!dataRef.current || !graph) return;
    const hl = highlight || { nodes: [], edges: [] };
    dataRef.current.nodes.update(graph.nodes.map((n) => nodeStyle(n, hl)));
    dataRef.current.edges.update(graph.edges.map((e) => edgeStyle(e, hl)));
    netRef.current?.unselectAll();
  }, [highlight, graph]);

  return <div ref={containerRef} className="graph-canvas" />;
}
