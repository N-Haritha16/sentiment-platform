# ingester/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

COPY backend/ /app/backend
COPY ingester/ /app/

COPY ingester/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "ingester.py"]
