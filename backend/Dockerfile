FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY backend ./backend

RUN pip install --no-cache-dir -r backend/requirements.txt

CMD ["python", "backend/main.py"]
