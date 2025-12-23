import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function SentimentChart({ data }) {
  if (!data || !data.length) return <div>No data</div>;

  const formattedData = data.map((d) => ({
    ...d,
    timestamp: new Date(d.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  }));

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-4">Sentiment Trend (Last 24 Hours)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#555" />
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="positive" stroke="#10b981" />
          <Line type="monotone" dataKey="negative" stroke="#ef4444" />
          <Line type="monotone" dataKey="neutral" stroke="#6b7280" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
