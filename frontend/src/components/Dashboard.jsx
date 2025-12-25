// frontend/src/components/Dashboard.jsx
import React, { useEffect, useMemo, useState } from "react";
import {
  fetchPosts,
  fetchDistribution,
  fetchAggregateData,
  connectWebSocket,
} from "../services/api";
import { DistributionChart } from "./DistributionChart";
import { SentimentChart } from "./SentimentChart";
import { LiveFeed } from "./LiveFeed";

export default function Dashboard() {
  const [distributionData, setDistributionData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [recentPosts, setRecentPosts] = useState([]);
  const [metrics, setMetrics] = useState({
    total: 0,
    positive: 0,
    negative: 0,
    neutral: 0,
  });
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [lastUpdate, setLastUpdate] = useState(null);

  // Initial REST data
  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      try {
        const [dist, agg, postsResp] = await Promise.all([
          fetchDistribution(24),
          fetchAggregateData("hour"),
          fetchPosts(20, 0, {}),
        ]);

        if (cancelled) return;

        setDistributionData(dist.distribution);
        setMetrics({
          total: dist.total,
          positive: dist.distribution.positive,
          negative: dist.distribution.negative,
          neutral: dist.distribution.neutral,
        });

        const mappedTrend = (agg.data || []).map((p) => ({
          timestamp: p.timestamp,
          positive: p.positive_count,
          negative: p.negative_count,
          neutral: p.neutral_count,
        }));
        setTrendData(mappedTrend);

        setRecentPosts(postsResp.posts || []);
        setLastUpdate(new Date().toLocaleTimeString());
      } catch (err) {
        console.error("Failed to load initial dashboard data", err);
      }
    }

    loadInitial();

    return () => {
      cancelled = true;
    };
  }, []);

  // WebSocket
  useEffect(() => {
    setConnectionStatus("connecting");

    const ws = connectWebSocket(
      (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "connected") {
            setConnectionStatus("connected");
          } else if (msg.type === "new_post") {
            const d = msg.data || {};
            const newPost = {
              post_id: d.post_id,
              source: d.source || "unknown",
              content: d.content || "",
              author: "unknown",
              created_at: d.timestamp,
              sentiment: d.sentiment_label
                ? {
                    label: d.sentiment_label,
                    confidence: d.confidence_score,
                    emotion: d.emotion || null,
                    model_name: null,
                  }
                : null,
            };
            setRecentPosts((prev) => [newPost, ...(prev || [])].slice(0, 50));
          } else if (msg.type === "metrics_update") {
            const data = msg.data || {};
            const last24 = data.last_24_hours || {
              total: 0,
              positive: 0,
              negative: 0,
              neutral: 0,
            };

            setMetrics({
              total: last24.total || 0,
              positive: last24.positive || 0,
              negative: last24.negative || 0,
              neutral: last24.neutral || 0,
            });

            setDistributionData({
              positive: last24.positive || 0,
              negative: last24.negative || 0,
              neutral: last24.neutral || 0,
            });
          }

          setLastUpdate(new Date().toLocaleTimeString());
        } catch (err) {
          console.error("Error handling WebSocket message", err);
        }
      },
      () => setConnectionStatus("disconnected"),
      () => setConnectionStatus("disconnected")
    );

    return () => {
      try {
        ws.close();
      } catch (err) {
        // ignore
      }
    };
  }, []);

  const statusDotClass = useMemo(() => {
    if (connectionStatus === "connected") return "bg-green-500";
    if (connectionStatus === "connecting") return "bg-yellow-400";
    return "bg-red-500";
  }, [connectionStatus]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
        <h1 className="text-2xl font-bold">
          Real-Time Sentiment Analysis Dashboard
        </h1>
        <div className="flex items-center space-x-4 mt-2 md:mt-0">
          <div className="flex items-center space-x-2">
            <span
              className={`inline-block w-3 h-3 rounded-full ${statusDotClass}`}
            />
            <span className="text-sm">
              Status:{" "}
              {connectionStatus === "connected"
                ? "Live"
                : connectionStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
            </span>
          </div>
          <div className="text-sm text-gray-400">
            Last Update: {lastUpdate || "—"}
          </div>
        </div>
      </div>

      {/* Distribution + Recent feed */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <DistributionChart data={distributionData} />
        <LiveFeed posts={recentPosts} />
      </div>

      {/* Trend over time */}
      <div className="mb-4">
        <SentimentChart data={trendData} />
      </div>

      {/* Metrics row (four boxes) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-sm text-gray-400">Total</div>
          <div className="text-2xl font-bold mt-1">{metrics.total}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-sm text-gray-400">Positive</div>
          <div className="text-2xl font-bold mt-1">{metrics.positive}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-sm text-gray-400">Negative</div>
          <div className="text-2xl font-bold mt-1">{metrics.negative}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-sm text-gray-400">Neutral</div>
          <div className="text-2xl font-bold mt-1">{metrics.neutral}</div>
        </div>
      </div>
    </div>
  );
}
