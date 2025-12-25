FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

COPY ingester/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingester/ ./
COPY backend/ ./backend

CMD ["python", "ingester.py"]
