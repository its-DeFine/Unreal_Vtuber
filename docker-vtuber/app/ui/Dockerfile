FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Environment variables with defaults
ENV UI_HOST=0.0.0.0
ENV UI_PORT=3000
ENV AUTOGEN_URL=http://autogen-agent:8000
ENV GRAPHFLOW_URL=http://graphflow-gateway:8080
ENV NEUROSYNC_URL=http://neurosync:5001
ENV NEUROSYNC_LOCAL_URL=http://neurosync-local:5000
ENV API_TIMEOUT=10
ENV DEBUG=false

# Run the application
CMD ["python", "app.py"]