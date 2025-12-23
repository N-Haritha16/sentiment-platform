import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

export default function DistributionChart({ data }) {
  const COLORS = { positive: "#10b981", negative: "#ef4444", neutral: "#6b7280" };
  const chartData = Object.entries(data)
    .filter(([_, value]) => value > 0)
    .map(([key, value]) => ({ name: key, value }));

  if (!chartData.length) return <div>No data</div>;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
      <PieChart width={250} height={250}>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          fill="#8884d8"
          label={(entry) => `${entry.name} (${entry.value})`}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </div>
  );
}
