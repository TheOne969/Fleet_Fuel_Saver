FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY analytics_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/shared_redis /shared/shared_redis
RUN pip install --no-cache-dir /shared/shared_redis
COPY analytics_engine/ .
CMD ["python", "worker.py"]

