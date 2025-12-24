// frontend/src/components/LiveFeed.jsx
import React from "react";

export function LiveFeed({ posts }) {
  const items = posts || [];

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full flex flex-col">
      <h3 className="text-lg font-semibold mb-4">Recent Posts Feed</h3>
      <div className="space-y-3 overflow-y-auto max-h-64 pr-2">
        {items.length === 0 && (
          <p className="text-gray-400 text-sm">No posts yet</p>
        )}

        {items.map((p) => (
          <div
            key={p.post_id}
            className="border border-gray-700 rounded-md p-2 text-sm"
          >
            <div className="flex justify-between mb-1">
              <span className="text-xs text-gray-400">{p.source}</span>
              <span className="text-xs text-gray-500">
                {p.created_at
                  ? new Date(p.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : ""}
              </span>
            </div>
            <p className="text-gray-100 truncate">{p.content}</p>

            {p.sentiment && (
              <div className="mt-1 text-xs text-gray-400">
                Sentiment:{" "}
                <span
                  className={
                    p.sentiment.label === "positive"
                      ? "text-green-400"
                      : p.sentiment.label === "negative"
                      ? "text-red-400"
                      : "text-gray-300"
                  }
                >
                  {p.sentiment.label}
                </span>
                {p.sentiment.emotion ? ` • ${p.sentiment.emotion}` : null}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
