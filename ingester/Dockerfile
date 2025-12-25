FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY backend ./backend
COPY ingester ./ingester

RUN pip install --no-cache-dir -r ingester/requirements.txt

CMD ["python", "ingester/ingester.py"]
