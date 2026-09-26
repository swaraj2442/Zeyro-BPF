import { useEffect, useRef } from 'react';
import { Network } from 'vis-network/standalone/esm/vis-network.mjs';
import { DataSet } from 'vis-data/standalone/esm/vis-data.mjs';

const TYPE_SHAPE = {
  exporter: 'dot',
  importer: 'dot',
  bank: 'square',
  factor: 'triangle',
};

function riskColor(score) {
  if (score > 70) return { background: '#c1543f', border: '#8a2f22' };
  if (score > 40) return { background: '#d8a559', border: '#b5813a' };
  return { background: '#ffffff', border: '#d8d2c4' };
}

export default function GraphView({ nodes, edges, onSelect, selectedId }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const visNodes = new DataSet(
      nodes.map((n) => {
        const colors = riskColor(n.risk_score);
        return {
          id: n.id,
          label: n.label,
          title: n.title,
          shape: TYPE_SHAPE[n.entity_type] || 'dot',
          size: n.entity_type === 'exporter' ? 16 + Math.min(n.risk_score / 5, 14) : 14,
          color: {
            background: colors.background,
            border: colors.border,
            highlight: { background: '#171614', border: '#171614' },
          },
          font: { color: '#1c1b19', size: 11, face: 'Inter' },
          borderWidth: 2,
        };
      })
    );

    const visEdges = new DataSet(
      edges.map((e, i) => ({
        id: i,
        from: e.source,
        to: e.target,
        color: { color: '#d8d2c4', opacity: 0.6 },
        width: 1,
        dashes: true,
        smooth: { type: 'continuous', roundness: 0.4 },
        arrows: { to: { enabled: true, scaleFactor: 0.4 } },
      }))
    );

    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -60, springLength: 90, springConstant: 0.06 },
        stabilization: { iterations: 150 },
      },
      interaction: { hover: true, tooltipDelay: 100 },
      layout: { improvedLayout: true },
    };

    const network = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);
    networkRef.current = network;

    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        onSelect(params.nodes[0]);
      }
    });

    return () => network.destroy();
  }, [nodes, edges]);

  useEffect(() => {
    if (networkRef.current && selectedId) {
      networkRef.current.selectNodes([selectedId]);
    }
  }, [selectedId]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}
