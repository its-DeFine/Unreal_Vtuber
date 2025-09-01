FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    docker-compose \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    docker \
    pyyaml \
    httpx \
    pydantic

# Copy application code
COPY management_agent.py /app/

# Create backup directory
RUN mkdir -p /backups

# Environment variables
ENV COMPOSE_FILE=/Unreal_Vtuber/docker-compose.yml \
    BACKUP_DIR=/backups \
    CLUSTER_NAME=vtuber-cluster

EXPOSE 8090

CMD ["python", "-m", "uvicorn", "management_agent:app", "--host", "0.0.0.0", "--port", "8090"]