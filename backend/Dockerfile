FROM python:3.11-slim

WORKDIR /app

# Avoid pip cache + increase timeout globally
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

# Copy only requirements first (Docker layer caching)
COPY requirements.txt .

# Upgrade pip ONLY (do NOT upgrade setuptools/wheel)
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Change this if worker uses a different entry
CMD ["python", "main.py"]
