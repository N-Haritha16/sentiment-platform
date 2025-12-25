# Real-Time Sentiment Analysis Platform

## Objective

This project implements a production-style, real-time sentiment analysis platform that ingests social media posts, analyzes sentiment and emotions using AI models, and visualizes results on a live dashboard. 

The platform demonstrates:

- Distributed microservices with Docker Compose. 
- Real-time processing using Redis Streams and consumer groups. 
- AI/ML integration (Hugging Face + external LLM placeholder). 
- WebSocket-based live updates to a React dashboard. 


## System Overview

The system consists of **6 containerized services**:

1. **Database (PostgreSQL)**  
   Stores posts, sentiment analysis results, and alerts. 

2. **Redis**  
   - Redis Streams: `XADD`, `XREADGROUP`, `XACK` for ingestion pipeline.  
   - Pub/Sub: broadcasts live updates to backend WebSocket. 

3. **Ingester Service**  
   - Generates realistic social media posts.  
   - Publishes to Redis Stream `social_posts_stream`. 

4. **Worker Service**  
   - Consumes from Redis Stream using consumer group `sentiment_workers`.  
   - Runs sentiment and emotion analysis with `SentimentAnalyzer`.  
   - Persists results to PostgreSQL.  
   - Publishes summarized post data to Redis Pub/Sub channel `sentiment_updates`. 

5. **Backend API Service (FastAPI)**  
   - REST endpoints for:
     - Health check (`/api/health`)  
     - Posts listing (`/api/posts`)  
     - Aggregated sentiment (`/api/sentiment/aggregate`)  
     - Sentiment distribution (`/api/sentiment/distribution`)  
   - WebSocket endpoint:
     - `/ws/sentiment` sends:
       - Connection notification  
       - New post updates from Redis Pub/Sub  
       - Periodic metrics updates using `SentimentAggregator`. 

6. **Frontend Dashboard Service (React + Vite)**  
   - Connects to REST + WebSocket.  
   - Displays charts, metrics cards, and live post feed. 

All services are orchestrated via `docker-compose.yml`. 

---

## Project Structure

sentiment-platform/
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
│
├── backend/
│ ├── Dockerfile
│ ├── requirements.txt
│ ├── main.py
│ ├── config.py
│ ├── api/
│ │ └── routes.py
│ ├── models/
│ │ └── models.py
│ ├── services/
│ │ ├── sentiment_analyzer.py
│ │ ├── aggregator.py
│ │ └── alerting.py
│ └── tests/
│ └── test_api.py
│
├── worker/
│ ├── Dockerfile
│ ├── requirements.txt
│ ├── worker.py
│ └── processor.py
│
├── ingester/
│ ├── Dockerfile
│ ├── requirements.txt
│ └── ingester.py
│
└── frontend/
├── Dockerfile
├── package.json
├── vite.config.js
├── index.html
└── src/
├── App.jsx
├── components/
│ ├── Dashboard.jsx
│ ├── SentimentChart.jsx
│ ├── DistributionChart.jsx
│ └── LiveFeed.jsx
└── services/
└── api.js


This matches the required structure in the assignment description. 



## Technology Stack

- **Backend API:** FastAPI (Python 3.9+)   
- **Database:** PostgreSQL 15+   
- **Message Queue:** Redis 7+ with Redis Streams and Pub/Sub 
- **Worker & Ingester:** Python async services  
- **Frontend:** React 18 + Vite + Recharts   
- **Containerization:** Docker + Docker Compose  
- **Tests:** pytest with FastAPI `TestClient` for backend API 



## Environment Configuration

Copy `.env.example` to `.env` and fill in values:

cp .env.example .env


## Key variables (PostgreSQL example): 

- **Database:**
POSTGRES_USER=sentiment_user
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=sentiment_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

- **Redis:**
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_STREAM_NAME=social_posts_stream
REDIS_CONSUMER_GROUP=sentiment_workers
REDIS_CACHE_PREFIX=sentiment_cache

- **AI Models:**
HUGGINGFACE_MODEL=distilbert-base-uncased-finetuned-sst-2-english
EMOTION_MODEL=j-hartmann/emotion-english-distilroberta-base
EXTERNAL_LLM_PROVIDER=groq
EXTERNAL_LLM_API_KEY=your_api_key_here
EXTERNAL_LLM_MODEL=llama-3.1-8b-instant

- **API / Frontend:**
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=3000
LOG_LEVEL=INFO

- **Alerting:**
ALERT_NEGATIVE_RATIO_THRESHOLD=2.0
ALERT_WINDOW_MINUTES=5
ALERT_MIN_POSTS=10


No real secrets should be committed; only sample values belong in `.env.example`. 


## Running the System

### 1. Build and start all services

From the root directory:

docker compose up -d --build



### 2. Verify services

- Check containers:

docker compose ps



- Expected ports:
  - Backend API: `http://localhost:8000`  
  - Frontend: `http://localhost:3000` 

### 3. Health check

Open or curl:

curl http://localhost:8000/api/health


Should return `200` with overall system status and service stats. 

## Using the Dashboard

- Open `http://localhost:3000` in a browser.   
- Dashboard shows:
  - Metrics cards (API status, total posts, last hour posts, WebSocket status).  
  - Sentiment trend chart over time.  
  - Sentiment distribution pie chart (last 24 hours).  
  - Live post feed, updated in real time.

New posts appear as the ingester publishes to Redis and the worker processes messages. WebSocket pushes `"post"` and `"metrics_update"` events to the frontend. 


## Testing

### Backend tests

Run tests inside backend container:

docker compose exec backend pytest -q


With coverage (if `pytest-cov` installed):

docker compose exec backend pytest --cov=backend --cov-report=term-missing


Current tests include:

- `/api/health` happy path.  
- `/api/posts` basic listing.  
- `/api/sentiment/aggregate` for multiple periods.  
- `/api/sentiment/distribution` default configuration. 

You can extend tests for sentiment analysis, emotion detection, and full integration flows to increase coverage. [file:1]

---

## Troubleshooting

- **Frontend 3000 not loading**  
  - Check: `docker compose logs frontend`  
  - Ensure `vite.config.js` exists and references port 3000.  

- **Backend 8000 not reachable**  
  - Check: `docker compose logs backend`  
  - Confirm database and Redis containers are healthy. 

- **No posts visible**  
  - Check ingester and worker logs:
    ```
    docker compose logs ingester
    docker compose logs worker
    ```
  - Verify Redis stream and consumer group names match `.env`. 

- **WebSocket not updating**  
  - Confirm frontend connects to `ws://localhost:8000/ws/sentiment`.  
  - Check backend logs for WebSocket or Redis Pub/Sub errors. 

