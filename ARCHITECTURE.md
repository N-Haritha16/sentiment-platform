# System Architecture

## Overview

This document describes the architecture of the real-time sentiment analysis platform, including services, data flow, and key design decisions. 

The system uses **6 containerized services** interconnected via PostgreSQL, Redis Streams, and HTTP/WebSocket. 

---

## High-Level Architecture

At a high level, the platform consists of:

- **Ingestion pipeline** (Ingester → Redis Streams → Worker → Database).  
- **Analytics & alerting** (Worker + Backend services).  
- **Visualization layer** (Backend API + WebSocket → React dashboard). 

All services are orchestrated using Docker Compose to enable zero-configuration startup. 

---

## Services

### Database Service (PostgreSQL)

- Stores:
  - `social_media_posts`
  - `sentiment_analysis`
  - `sentiment_alerts` 
  - Exposed only to backend and worker services on the internal Docker network. 
- Not exposed to host (no published ports). 

### Redis Service

- Provides:
  - Redis Streams:
    - Stream: `social_posts_stream`
    - Consumer group: `sentiment_workers`
    - Used by Ingester and Worker for at-least-once delivery with `XREADGROUP` and `XACK`. 
  - Pub/Sub:
    - Channel: `sentiment_updates`
    - Used by Worker to push new post updates.
    - Backend WebSocket subscribes and broadcasts messages to clients. 
- Internal-only; not exposed to host. 

### Ingester Service

- Script: `ingester/ingester.py`.  
- Responsibilities:
  - Generate synthetic social media posts (text, author, source, timestamps).  
  - Publish each post to Redis Stream `social_posts_stream` with fields:
    - `post_id`, `source`, `content`, `author`, `created_at`. 
  - Configurable rate via environment variables. 

### Worker Service

- Script: `worker/worker.py`.  
- Uses Redis consumer group `sentiment_workers` to read from `social_posts_stream`. 
- For each message:
  - Decode payload and validate required fields.  
  - Analyze sentiment and emotion using `SentimentAnalyzer`:
    - Primary: local Hugging Face model (`HUGGINGFACE_MODEL`). 
    - Fallback: external LLM via configured provider (Groq placeholder). 
  - Save post and analysis using `processor.save_post_and_analysis` into PostgreSQL. 
  - Publish a summarized “new post” event to Redis Pub/Sub `sentiment_updates`:
    - Includes `post_id`, preview of `content`, `source`, `sentiment_label`, `confidence_score`, `emotion`, and timestamp. 
  - `XACK` the message to mark it processed. 

The worker maintains counters for processed and failed messages, useful for monitoring. 

### Backend API Service (FastAPI)

Entry point: `backend/main.py`.  
Key components:

- **Configuration:** `backend/config.py` reads environment variables (`DATABASE_URL`, Redis settings, model names, alert thresholds). 

- **Models:** `backend/models/models.py` defines SQLAlchemy models:
  - `SocialMediaPost`
  - `SentimentAnalysis`
  - `SentimentAlert`
  - Async session factory and `get_db_session` dependency. 

- **Services:**
  - `sentiment_analyzer.py`:
    - Local Hugging Face pipeline for sentiment.
    - Emotion detection model for fine-grained categories. 
  - `aggregator.py`:
    - `SentimentAggregator` computes:
      - Time-bucketed sentiment counts and averages.  
      - Distribution metrics over configurable time windows.  
    - Uses Redis for optional caching of aggregate metrics.
  - `alerting.py`:
    - `AlertService` monitors negative/positive ratio over a sliding window.
    - Writes rows to `sentiment_alerts` when thresholds exceeded. 

- **API Routes:** `backend/api/routes.py`

  - `GET /api/health`:
    - Checks DB connectivity and counts posts.
    - Pings Redis to verify availability.
    - Returns overall status and basic stats. 

  - `GET /api/posts`:
    - Returns paginated list of posts with optional filters:
      - `source`, `sentiment`, `start_date`, `end_date`.
    - Includes joined sentiment analysis data (label, confidence, emotion, model name). 

  - `GET /api/sentiment/aggregate`:
    - Aggregates sentiment into time buckets (`minute`, `hour`, `day`).  
    - Returns counts and percentages per bucket plus overall summary. 

  - `GET /api/sentiment/distribution`:
    - Computes overall positive/negative/neutral counts and percentages over a given hour window (default 24h). 

  - `WebSocket /ws/sentiment`:
    - On connect:
      - Adds client to `ConnectionManager`.
      - Sends `{ "type": "connected", ... }`.  
    - Subscribes to Redis Pub/Sub `sentiment_updates` and forwards messages:
      - Messages of form `{ "type": "post", "data": {...} }` go to all clients.  
    - Runs periodic metrics task (e.g., every 30s) using `SentimentAggregator.get_distribution` for:
      - Last minute (1h configured), last 60h, last 24h.
      - Broadcasts `{ "type": "metrics_update", ... }` payload. 

### Frontend Dashboard Service (React + Vite)

Key files:

- `src/App.jsx`: root component, renders `Dashboard`.  
- `src/services/api.js`: HTTP client for REST endpoints.  
- `src/components/Dashboard.jsx`:
  - Loads initial data via REST:
    - `/api/health`
    - `/api/sentiment/aggregate`
    - `/api/sentiment/distribution`
    - `/api/posts`
  - Opens WebSocket to `/ws/sentiment`.  
  - Updates state in response to:
    - `"post"` events: prepend to live feed.  
    - `"metrics_update"` events: update distribution and metrics. 

- `SentimentChart.jsx`:
  - Uses Recharts `LineChart` to plot positive, negative, neutral counts over time. 

- `DistributionChart.jsx`:
  - Uses Recharts `PieChart` to show sentiment ratio for last 24 hours. 

- `LiveFeed.jsx`:
  - Scrollable list of recent posts with basic sentiment and emotion labels. 

---

## Data Model

### Tables

1. **social_media_posts**

   - `id` (PK, auto-increment)  
   - `post_id` (unique external ID)  
   - `source` (e.g., "twitter", "reddit")  
   - `content` (text body)  
   - `author`  
   - `created_at` (original timestamp)  
   - `ingested_at` (when it entered the system) 

2. **sentiment_analysis**

   - `id` (PK)  
   - `post_id` (FK → social_media_posts.post_id)  
   - `model_name`  
   - `sentiment_label` (positive, negative, neutral)  
   - `confidence_score` (float)  
   - `emotion` (e.g., joy, anger, sadness, fear, surprise, neutral)  
   - `analyzed_at` (timestamp). 

3. **sentiment_alerts**

   - `id` (PK)  
   - `alert_type` (e.g., "high_negative_ratio")  
   - `threshold_value`  
   - `actual_value`  
   - `window_start`, `window_end`  
   - `post_count`  
   - `triggered_at`  
   - `details` (JSON). 

Indexes are defined on frequently queried fields such as `created_at`, `analyzed_at`, and `sentiment_label` to support time-based queries and aggregations. 

---

## Data Flow

### Ingestion to Storage

1. Ingester publishes posts to Redis Stream `social_posts_stream`.  
2. Worker `XREADGROUP`s messages using group `sentiment_workers`.  
3. Worker runs sentiment and emotion analysis, then writes:
   - `social_media_posts` row.  
   - `sentiment_analysis` row linked via `post_id`. 
4. Worker publishes a summarized event to Redis Pub/Sub `sentiment_updates`. 

### Real-Time Updates to Dashboard

1. Backend WebSocket subscribes to `sentiment_updates`. 
2. When Worker publishes a new post event:
   - Backend receives Pub/Sub message.
   - Broadcasts it to all WebSocket clients. 
3. Frontend Live Feed updates in real time without page reload. 

### Aggregations and Alerts

- `SentimentAggregator`:
  - Computes bucketed aggregates and distributions for API and WebSocket metrics.  
  - Optionally uses Redis cache to avoid repeated heavy queries. 

- `AlertService`:
  - Periodically checks recent window (e.g., last 5 minutes) for negative-to-positive ratio.
  - If threshold is exceeded and minimum posts condition met, inserts a new row into `sentiment_alerts`. 

---

## Deployment and Ports

- **Frontend:** exposed on host port `3000`.   
- **Backend API:** exposed on host port `8000`.   
- **PostgreSQL & Redis:** internal only; reachable by backend and worker via Docker network, not by host directly. 

Docker Compose handles dependency order so that database and Redis are available before backend and worker begin processing. 

---

## Future Improvements

- Add dedicated alert viewing endpoints and UI panel.  
- Implement more advanced emotion visualizations over time.  
- Integrate real external LLM provider with configuration-based switching.  
- Expand automated tests for worker, sentiment analyzer, and full E2E ingestion-to-dashboard path. 
