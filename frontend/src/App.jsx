// api.js
const API_BASE_URL = "http://localhost:8000/api"; // replace with your actual backend URL
let ws = null;

/**
 * Fetch posts with optional filters
 * @param {number} limit - number of posts to fetch
 * @param {number} offset - pagination offset
 * @param {object} filters - {source, sentiment, start_date, end_date}
 */
export async function fetchPosts(limit = 50, offset = 0, filters = {}) {
  const params = new URLSearchParams({
    limit,
    offset,
    ...filters,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/posts?${params.toString()}`);
    if (!response.ok) {
      throw new Error("Failed to fetch posts");
    }
    return await response.json();
  } catch (err) {
    console.error("fetchPosts error:", err);
    return { posts: [], total: 0 };
  }
}

/**
 * Fetch sentiment distribution over last X hours
 * @param {number} hours - timeframe in hours
 * @param {string} source - optional source filter
 */
export async function fetchDistribution(hours = 24, source = "") {
  const params = new URLSearchParams({ hours });
  if (source) params.append("source", source);

  try {
    const response = await fetch(`${API_BASE_URL}/sentiment/distribution?${params.toString()}`);
    if (!response.ok) {
      throw new Error("Failed to fetch distribution");
    }
    return await response.json();
  } catch (err) {
    console.error("fetchDistribution error:", err);
    return { distribution: { positive: 0, negative: 0, neutral: 0 }, total: 0 };
  }
}

/**
 * Fetch sentiment aggregate data (time buckets)
 * @param {string} period - "minute" | "hour" | "day"
 * @param {string} startDate - ISO string
 * @param {string} endDate - ISO string
 * @param {string} source - optional source filter
 */
export async function fetchAggregateData(period = "hour", startDate, endDate, source = "") {
  const params = new URLSearchParams({ period });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  if (source) params.append("source", source);

  try {
    const response = await fetch(`${API_BASE_URL}/sentiment/aggregate?${params.toString()}`);
    if (!response.ok) {
      throw new Error("Failed to fetch aggregate data");
    }
    return await response.json();
  } catch (err) {
    console.error("fetchAggregateData error:", err);
    return { data: [], summary: {} };
  }
}

/**
 * Connect to WebSocket for live sentiment updates
 * @param {function} onMessage - callback when a new message arrives
 * @param {function} onError - callback on WebSocket error
 * @param {function} onClose - callback on WebSocket close
 */
export function connectWebSocket(onMessage, onError, onClose) {
  ws = new WebSocket("ws://localhost:8000/ws/sentiment"); // replace with your backend WS URL

  ws.onopen = () => {
    console.log("WebSocket connected");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage && onMessage(data);
    } catch (err) {
      console.error("WebSocket message parse error:", err);
    }
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
    onError && onError(err);
  };

  ws.onclose = (event) => {
    console.log("WebSocket closed:", event);
    onClose && onClose(event);
  };

  return ws;
}

/**
 * Optional: disconnect WebSocket
 */
export function disconnectWebSocket() {
  if (ws) {
    ws.close();
    ws = null;
  }
}
