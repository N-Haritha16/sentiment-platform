FROM python:3.11-slim

WORKDIR /app

# Avoid pip cache + increase timeout (important for torch)
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

CMD ["python", "worker.py"]
