FROM python:3.11-slim
WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

COPY backend/ /app/backend
COPY worker/ /app/

COPY worker/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "worker.py"]
