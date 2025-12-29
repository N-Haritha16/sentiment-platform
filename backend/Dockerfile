# backend/Dockerfile
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy backend code
COPY backend/ /app/backend

# Install dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path so 'backend' can be imported anywhere
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
