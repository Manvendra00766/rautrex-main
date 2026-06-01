FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirements.txt .

# Install Python dependencies including the missing ones
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir prometheus-fastapi-instrumentator sentry-sdk aiosqlite alembic

# Copy the backend code into the container
COPY backend/ .

# Expose the port
EXPOSE 7860

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
