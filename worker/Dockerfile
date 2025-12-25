FROM python:3.11-slim

WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY . .

# Copy backend code so imports work
COPY ../backend ./backend

# Run worker
CMD ["python", "worker.py"]
