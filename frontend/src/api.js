const BASE_URL = 'http://localhost:8000';

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post(path) {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'POST' });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  health: () => get('/health'),
  entities: (limit) => get(`/entities${limit ? `?limit=${limit}` : ''}`),
  entity: (id) => get(`/entities/${id}`),
  graph: (limit = 60) => get(`/graph?limit=${limit}`),
  regenerate: (seed) => post(`/regenerate${seed ? `?seed=${seed}` : ''}`),
};
