FROM python:3.12-slim
WORKDIR /app
COPY ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/shared_proto /shared/shared_proto
RUN pip install --no-cache-dir /shared/shared_proto
COPY ingestion_service/ .
CMD ["python", "server.py"]

