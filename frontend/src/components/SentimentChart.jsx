// frontend/src/components/SentimentChart.jsx
import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function SentimentChart({ data }) {
  const items = data || [];

  if (items.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 h-full flex flex-col justify-center items-center">
        <h3 className="text-lg font-semibold mb-2">
          Sentiment Trend (Last 24 Hours)
        </h3>
        <p className="text-gray-400 text-sm">No data available</p>
      </div>
    );
  }

  const chartData = items.map((d) => ({
    ...d,
    time: formatTime(d.timestamp),
  }));

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h3 className="text-lg font-semibold mb-4">
        Sentiment Trend (Last 24 Hours)
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="time" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="positive"
              name="Positive"
              stroke="#10b981"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="negative"
              name="Negative"
              stroke="#ef4444"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="neutral"
              name="Neutral"
              stroke="#6b7280"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
