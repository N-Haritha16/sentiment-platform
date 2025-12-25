FROM python:3.11-slim

WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY worker/ ./

# Copy backend code so imports work
COPY backend/ ./backend

CMD ["python", "worker.py"]
