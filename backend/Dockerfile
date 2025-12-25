FROM python:3.11-slim

WORKDIR /app

# Upgrade pip with retries
RUN python -m pip install --upgrade pip setuptools wheel --timeout 120 --retries 5

# Copy requirements and install with retries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --timeout 120 --retries 5

# Copy rest of the code
COPY . .

CMD ["python", "main.py"]  # backend entrypoint
