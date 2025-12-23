import { useEffect, useState, useRef } from "react";

export default function LiveFeed() {
  const [posts, setPosts] = useState([]);
  const feedEndRef = useRef(null);

  useEffect(() => {
    // Example: WebSocket connection
    const ws = new WebSocket("wss://your-websocket-url"); // replace with your actual URL

    ws.onopen = () => {
      console.log("Connected to live feed");
    };

    ws.onmessage = (event) => {
      const post = JSON.parse(event.data);
      setPosts((prev) => [post, ...prev].slice(0, 50)); // keep latest 50 posts
    };

    ws.onclose = () => console.log("Disconnected from live feed");

    return () => ws.close();
  }, []);

  useEffect(() => {
    // Scroll to top whenever posts update
    if (feedEndRef.current) {
      feedEndRef.current.scrollTop = 0;
    }
  }, [posts]);

  return (
    <div className="bg-gray-800 rounded-lg p-4 flex flex-col h-96">
      <h3 className="text-lg font-semibold mb-4">Recent Posts Feed</h3>
      <div
        className="overflow-y-auto flex-1 space-y-2"
        ref={feedEndRef}
      >
        {posts.length === 0 ? (
          <p className="text-gray-400 text-sm">No posts yet...</p>
        ) : (
          posts.map((post) => (
            <div
              key={post.post_id}
              className={`p-2 rounded border-l-4 ${
                post.sentiment === "positive"
                  ? "border-green-400 bg-gray-700"
                  : post.sentiment === "negative"
                  ? "border-red-400 bg-gray-700"
                  : "border-gray-400 bg-gray-700"
              }`}
            >
              <p className="text-sm">{post.content}</p>
              <p className="text-xs text-gray-400">
                Sentiment: {post.sentiment} | ID: {post.post_id}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
