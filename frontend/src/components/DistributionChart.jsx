// frontend/src/components/DistributionChart.jsx
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = {
  positive: "#10b981",
  negative: "#ef4444",
  neutral: "#6b7280",
};

export function DistributionChart({ data }) {
  const hasData =
    data &&
    (data.positive !== 0 || data.negative !== 0 || data.neutral !== 0);

  if (!hasData) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 h-full flex flex-col justify-center items-center">
        <h3 className="text-lg font-semibold mb-2">Sentiment Distribution</h3>
        <p className="text-gray-400 text-sm">No data available</p>
      </div>
    );
  }

  const total = data.positive + data.negative + data.neutral;

  const items = [
    { key: "positive", label: "Positive", value: data.positive },
    { key: "negative", label: "Negative", value: data.negative },
    { key: "neutral", label: "Neutral", value: data.neutral },
  ].filter((x) => x.value > 0);

  const chartData = items.map((x) => ({
    name: x.label,
    key: x.key,
    value: x.value,
    pct: total ? ((x.value / total) * 100).toFixed(1) : "0.0",
  }));

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius="80%"
              label={(entry) => `${entry.name} (${entry.pct}%)`}
            >
              {chartData.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={COLORS[entry.key] || "#6b7280"}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name, props) => [
                `${value} (${props.payload.pct}%)`,
                name,
              ]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
