import React from "react";
import ReactDOM from "react-dom/client";
import Dashboard from "./components/Dashboard";

function App() {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "16px" }}>
      <h1>Sentiment Analysis Dashboard</h1>
      <Dashboard />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
export default App;
