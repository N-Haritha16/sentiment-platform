FROM python:3.11-slim

WORKDIR /app

# Copy ingester requirements and install
COPY ingester/requirements.txt ./ingester/
RUN pip install --no-cache-dir -r ./ingester/requirements.txt

# Copy the entire project
COPY . .

# Set PYTHONPATH so ingester can import backend
ENV PYTHONPATH=/app

# Set entrypoint for ingester
CMD ["python", "ingester/ingester.py"]
