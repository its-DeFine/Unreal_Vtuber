# Multi-stage build for autonomous agent
FROM node:23.3.0-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    g++ \
    git \
    make \
    python3 \
    unzip \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install bun and create python symlink
RUN npm install -g bun@1.2.5
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy package files
COPY package.json ./
COPY tsconfig.json ./

# Install dependencies
ENV HUSKY=0
RUN bun install --no-cache --trust-all-scripts

# Copy source code
COPY src ./src

# Build the application
RUN bun run build

# Production stage
FROM node:23.3.0-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    python3 \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install bun
RUN npm install -g bun@1.2.5

# Copy built application from builder stage
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/src ./src

# Create directories for data and logs
RUN mkdir -p /app/data/uploads /app/logs

# Set environment variables
ENV NODE_ENV=production
ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autonomous_agent

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Add logging configuration
RUN echo '#!/bin/bash\necho "Starting autonomous agent with database connection..."\necho "Database URL: $DATABASE_URL"\nexec "$@"' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["bun", "run", "start"] 