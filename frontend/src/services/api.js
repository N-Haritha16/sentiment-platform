// frontend/src/services/api.js

const API_BASE =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE) ||
  "http://localhost:8000";

// GET /api/posts
export async function fetchPosts(limit = 20, offset = 0, filters = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (filters.source) params.set("source", filters.source);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);

  const res = await fetch(`${API_BASE}/api/posts?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch posts");
  return res.json();
}

// GET /api/sentiment/distribution
export async function fetchDistribution(hours = 24) {
  const params = new URLSearchParams();
  params.set("hours", String(hours));

  const res = await fetch(
    `${API_BASE}/api/sentiment/distribution?${params.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch distribution");
  return res.json();
}

// GET /api/sentiment/aggregate
export async function fetchAggregateData(period = "hour", startDate, endDate) {
  const params = new URLSearchParams();
  params.set("period", period);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);

  const res = await fetch(
    `${API_BASE}/api/sentiment/aggregate?${params.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch aggregate data");
  return res.json();
}

// WebSocket connection helper -> /ws/sentiment
export function connectWebSocket(onMessage, onError, onClose) {
  let wsBase;
  try {
    const url = new URL(API_BASE);
    const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
    wsBase = `${wsProtocol}//${url.host}`;
  } catch (e) {
    wsBase = API_BASE.replace(/^http/, "ws");
  }

  const ws = new WebSocket(`${wsBase}/ws/sentiment`);

  ws.onmessage = onMessage;
  if (onError) ws.onerror = onError;
  if (onClose) ws.onclose = onClose;

  return ws;
}
