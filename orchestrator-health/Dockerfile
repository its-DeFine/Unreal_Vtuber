FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

ARG CACHE_BUST=1
COPY orchestrator_health /app/orchestrator_health

CMD ["python", "-m", "orchestrator_health.remote_health_service"]
