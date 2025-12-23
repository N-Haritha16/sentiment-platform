import { useEffect, useState } from "react";
import DistributionChart from "./DistributionChart";
import SentimentChart from "./SentimentChart";
import LiveFeed from "./LiveFeed";

export default function Dashboard() {
  const [distributionData, setDistributionData] = useState({
    positive: 0,
    negative: 0,
    neutral: 0,
  });
  const [trendData, setTrendData] = useState([]);
  const [metrics, setMetrics] = useState({
    total: 0,
    positive: 0,
    negative: 0,
    neutral: 0,
  });
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    // Fetch initial metrics and charts
    fetch("/api/sentiment/distribution?hours=24")
      .then((res) => res.json())
      .then((data) => {
        setDistributionData(data.distribution);
        setMetrics({
          total: data.total,
          positive: data.distribution.positive,
          negative: data.distribution.negative,
          neutral: data.distribution.neutral,
        });
        setLastUpdate(new Date(data.cached_at).toLocaleTimeString());
      });

    fetch("/api/sentiment/aggregate?period=hour")
      .then((res) => res.json())
      .then((data) => {
        const trend = data.data.map((d) => ({
          timestamp: d.timestamp,
          positive: d.positive_count,
          negative: d.negative_count,
          neutral: d.neutral_count,
        }));
        setTrendData(trend);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Real-Time Sentiment Analysis Dashboard</h1>
        <span className="text-green-400">● Live</span>
        {lastUpdate && <span>Last Update: {lastUpdate}</span>}
      </div>

      {/* Distribution + Live Feed */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DistributionChart data={distributionData} />
        <LiveFeed />
      </div>

      {/* Trend chart */}
      <SentimentChart data={trendData} />

      {/* Metrics cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total" value={metrics.total} />
        <MetricCard label="Positive" value={metrics.positive} color="green" />
        <MetricCard label="Negative" value={metrics.negative} color="red" />
        <MetricCard label="Neutral" value={metrics.neutral} color="gray" />
      </div>
    </div>
  );
}

function MetricCard({ label, value, color = "white" }) {
  const colorClasses = {
    white: "text-white",
    green: "text-green-400",
    red: "text-red-400",
    gray: "text-gray-400",
  };
  return (
    <div className="bg-gray-800 rounded-lg p-4 text-center">
      <p className="text-sm">{label}</p>
      <p className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</p>
    </div>
  );
}
