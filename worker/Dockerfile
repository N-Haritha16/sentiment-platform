FROM python:3.11-slim

WORKDIR /app

# copy backend so worker can import it
COPY ../backend /app/backend
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "worker.py"]
