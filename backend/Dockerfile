FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Upgrade pip first to avoid JSON decode errors
RUN python -m pip install --upgrade pip setuptools wheel

# Then install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
