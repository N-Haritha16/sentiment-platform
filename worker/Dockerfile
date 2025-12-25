FROM python:3.11-slim

WORKDIR /app

# Upgrade pip with retries
RUN python -m pip install --upgrade pip setuptools wheel --timeout 120 --retries 5

# Copy worker requirements and install
COPY worker/requirements.txt ./worker/
RUN pip install --no-cache-dir -r ./worker/requirements.txt --timeout 120 --retries 5

# Copy entire project
COPY . .

# Set PYTHONPATH so worker can import backend
ENV PYTHONPATH=/app

# Set entrypoint for worker
CMD ["python", "worker/worker.py"]
