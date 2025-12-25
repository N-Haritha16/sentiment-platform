FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ../backend ./backend

CMD ["python", "ingester.py"]
