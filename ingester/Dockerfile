FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY ingester /app/ingester

WORKDIR /app/ingester

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "ingester.py"]
