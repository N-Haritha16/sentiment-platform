FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY backend /app/backend
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "-m", "backend.main"]
