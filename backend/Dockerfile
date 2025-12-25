FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

# COPY requirements from current context (./backend)
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY .. /app

ENV PYTHONPATH=/app

CMD ["python", "backend/main.py"]
