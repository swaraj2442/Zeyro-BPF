import { useEffect, useState, useCallback } from 'react';
import { api } from './api';
import TopNav from './components/TopNav';
import GraphView from './components/GraphView';
import SidePanel from './components/SidePanel';
import FeatureRow from './components/FeatureRow';
import Legend from './components/Legend';

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [entities, setEntities] = useState([]);
  const [health, setHealth] = useState({ entities: 0, transactions: 0 });
  const [selectedId, setSelectedId] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [activeTab, setActiveTab] = useState('Overview');
  const [activeWorkflow, setActiveWorkflow] = useState('Investigation');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, e, h] = await Promise.all([api.graph(60), api.entities(), api.health()]);
      setGraph(g);
      setEntities(e);
      setHealth(h);

      // Auto-select the highest-risk entity so the demo opens with a flagged case
      const topRisk = [...e].sort((a, b) => b.risk_score - a.risk_score)[0];
      if (topRisk) {
        setSelectedId(topRisk.entity_id);
        setSelectedEntity(topRisk);
      }
    } catch (err) {
      setError('Cannot reach Trade Sentinel API at localhost:8000. Is `uvicorn api:app` running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelect = async (id) => {
    setSelectedId(id);
    const found = entities.find((e) => e.entity_id === id);
    if (found) {
      setSelectedEntity(found);
    } else {
      try {
        const detail = await api.entity(id);
        setSelectedEntity(detail);
      } catch {
        /* ignore */
      }
    }
  };

  const handleRegenerate = async () => {
    await api.regenerate();
    await loadData();
  };

  const topRisk = entities.length > 0 ? [...entities].sort((a, b) => b.risk_score - a.risk_score)[0] : null;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <TopNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onRegenerate={handleRegenerate}
        entityCount={health.entities}
        txCount={health.transactions}
      />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, position: 'relative', background: 'var(--bg)' }}>
          {error ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: 13, padding: 40, textAlign: 'center' }}>
              {error}
            </div>
          ) : loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-faint)', fontSize: 13 }}>
              Loading transaction graph…
            </div>
          ) : (
            <>
              <GraphView nodes={graph.nodes} edges={graph.edges} onSelect={handleSelect} selectedId={selectedId} />
              <Legend topRisk={topRisk} />
            </>
          )}
        </div>

        <SidePanel entity={selectedEntity} activeWorkflow={activeWorkflow} onWorkflowChange={setActiveWorkflow} />
      </div>

      <FeatureRow />
    </div>
  );
}
