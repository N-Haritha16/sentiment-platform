import React, { useEffect, useState } from "react";
import SentimentChart from "./SentimentChart";
import DistributionChart from "./DistributionChart";
import LiveFeed from "./LiveFeed";

const Dashboard = () => {
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [metrics, setMetrics] = useState({
    total: 0,
    positive: 0,
    negative: 0,
    neutral: 0,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2>Real-Time Sentiment Analysis Dashboard</h2>
        <div style={styles.headerRight}>
          <span style={styles.liveStatus}>● Live</span>
          <span>
            Last Update: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Top Row */}
      <div style={styles.topRow}>
        <div style={styles.card}>
          <h3>Distribution</h3>
          <DistributionChart />
        </div>

        <div style={styles.card}>
          <h3>Recent Posts Feed</h3>
          <LiveFeed />
        </div>
      </div>

      {/* Middle Row */}
      <div style={styles.fullRow}>
        <h3>Sentiment Trend Over Time</h3>
        <SentimentChart />
      </div>

      {/* Metrics Row */}
      <div style={styles.metricsRow}>
        <MetricCard title="Total" value={metrics.total} />
        <MetricCard title="Positive" value={metrics.positive} />
        <MetricCard title="Negative" value={metrics.negative} />
        <MetricCard title="Neutral" value={metrics.neutral} />
      </div>
    </div>
  );
};

const MetricCard = ({ title, value }) => (
  <div style={styles.metricCard}>
    <h4>{title}</h4>
    <p>{value}</p>
  </div>
);

const styles = {
  container: {
    padding: "20px",
    fontFamily: "Arial, sans-serif",
    backgroundColor: "#f5f7fa",
    minHeight: "100vh",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px",
  },
  headerRight: {
    display: "flex",
    gap: "15px",
    alignItems: "center",
    fontSize: "14px",
  },
  liveStatus: {
    color: "green",
    fontWeight: "bold",
  },
  topRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px",
    marginBottom: "20px",
  },
  fullRow: {
    backgroundColor: "#fff",
    padding: "15px",
    borderRadius: "8px",
    marginBottom: "20px",
  },
  card: {
    backgroundColor: "#fff",
    padding: "15px",
    borderRadius: "8px",
    height: "100%",
  },
  metricsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "15px",
  },
  metricCard: {
    backgroundColor: "#fff",
    padding: "15px",
    borderRadius: "8px",
    textAlign: "center",
    fontWeight: "bold",
  },
};

export default Dashboard;
