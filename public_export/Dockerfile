FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
# Install system dependencies if required for grpc
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Default entrypoint for FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# If you want to run the standalone app.py instead, use:
# CMD ["python", "app.py"]
