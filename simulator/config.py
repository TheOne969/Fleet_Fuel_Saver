import os

# Where to send the gRPC stream
INGESTION_HOST = os.getenv("INGESTION_HOST", "localhost:50051")

# Telemetry frequency
TICK_RATE_MS = int(os.getenv("TICK_RATE_MS", 100))