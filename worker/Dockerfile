FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY backend ./backend
COPY worker ./worker

RUN pip install --no-cache-dir -r worker/requirements.txt

CMD ["python", "worker/worker.py"]
