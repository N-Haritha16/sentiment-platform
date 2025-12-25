FROM python:3.11-slim

WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy the entire project
COPY . .

# Set PYTHONPATH so other services can import backend
ENV PYTHONPATH=/app

# Set the entrypoint for backend
CMD ["python", "backend/main.py"]
