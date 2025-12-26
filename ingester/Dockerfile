
FROM python:3.11-slim
WORKDIR /ingester

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "ingester.py"]

