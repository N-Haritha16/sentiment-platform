# Backend Dockerfile snippet
FROM python:3.11-slim

WORKDIR /app

# Upgrade pip, setuptools, wheel with retries and increased timeout
RUN python -m pip install --upgrade pip setuptools wheel --timeout 120 --retries 5

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --timeout 120 --retries 5

# Copy the rest of the code
COPY . .
