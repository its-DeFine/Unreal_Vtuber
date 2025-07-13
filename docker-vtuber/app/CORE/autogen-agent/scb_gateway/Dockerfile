FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the gateway code
COPY . .

# Expose the port
EXPOSE 8300

# Run the gateway
CMD ["uvicorn", "scb_gateway:app", "--host", "0.0.0.0", "--port", "8300"] 