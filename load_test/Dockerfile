FROM python:3.12-slim

WORKDIR /app

# Install standard dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY load_test/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared proto
COPY shared/shared_proto /shared/shared_proto
RUN pip install --no-cache-dir /shared/shared_proto

COPY load_test/ .

CMD ["python", "main.py"]

