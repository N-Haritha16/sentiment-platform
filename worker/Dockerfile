FROM python:3.11-slim

WORKDIR /app

# copy shared backend code
COPY backend /app/backend

# copy worker code
COPY worker /app/worker

WORKDIR /app/worker

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "worker.py"]
