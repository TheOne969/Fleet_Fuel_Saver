FROM python:3.12-slim
WORKDIR /app
COPY simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/shared_proto /shared/shared_proto
RUN pip install --no-cache-dir /shared/shared_proto
COPY simulator/ .
CMD ["python", "main.py"]

