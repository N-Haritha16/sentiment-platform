# Architecture

## Services

- Database (PostgreSQL): Stores posts, sentiment analysis, alerts.
- Redis (Streams): Message queue for posts and cache for aggregates.
- Ingester: Publishes simulated social media posts to Redis Streams.
- Worker: Consumes posts, runs sentiment and emotion analysis, stores results.
- Backend API: FastAPI service exposing REST endpoints and WebSocket.
- Frontend: React dashboard for charts and live feed.

Detailed diagrams and flows will be added after implementation.
