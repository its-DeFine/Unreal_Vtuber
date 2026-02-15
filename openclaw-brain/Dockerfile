FROM node:20-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl python3 build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install OpenClaw CLI globally
RUN npm install -g @openclaw/cli 2>/dev/null || echo "OpenClaw CLI not yet published; will use local gateway"

# Copy package manifests and install deps
COPY package.json package-lock.json* ./
RUN npm install --production

# Copy application code
COPY . .

RUN chmod +x start.sh

# Volumes for persistent data
VOLUME ["/data/memory", "/workspace"]

# OpenClaw gateway port + chat-shim port
EXPOSE 18789 18801

ENTRYPOINT ["./start.sh"]
