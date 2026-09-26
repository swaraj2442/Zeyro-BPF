const BASE_URL = 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `API error ${res.status}`);
  }
  return res.json();
}

const post = (path, body) => request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });

export const api = {
  health: () => request('/health'),
  cases: () => request('/cases'),
  caseDetail: (id) => request(`/cases/${id}`),
  inputs: (id) => request(`/cases/${id}/inputs`),
  context: (entityId, caseId) => request(`/entities/${entityId}/context?case=${caseId}`),
  narrate: (caseId, step) => post('/chat', { case_id: caseId, step, mode: 'narrate' }),
  ask: (caseId, step, message, history) => post('/chat', { case_id: caseId, step, mode: 'ask', message, history }),
  feedback: (caseId, verdict) => post('/feedback', { case_id: caseId, verdict }),
  feedbackMap: () => request('/feedback'),
  reset: () => post('/reset'),
};
