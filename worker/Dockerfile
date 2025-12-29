# worker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy backend first so worker can import it
COPY backend/ /app/backend
# Copy worker code
COPY worker/ /app/

# Install dependencies
COPY worker/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "worker.py"]
