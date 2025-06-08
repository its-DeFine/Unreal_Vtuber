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

# Copy package files and build configuration
COPY package.json ./
COPY tsconfig.json ./
COPY tsconfig.build.json ./
COPY tsup.config.ts ./

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
COPY --from=builder /app/tsconfig.json ./
COPY --from=builder /app/tsconfig.build.json ./
COPY --from=builder /app/tsup.config.ts ./

# Create directories for data and logs
RUN mkdir -p /app/data/uploads /app/logs

# Set environment variables
ENV NODE_ENV=production
ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autonomous_agent

# Expose port
EXPOSE 3000

# Health check - Updated to use the correct API health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Enhanced entrypoint script with database connection testing
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting autonomous agent with database connection..."\n\
echo "📊 Environment Information:"\n\
echo "   - Database URL: $DATABASE_URL"\n\
echo "   - Node Environment: $NODE_ENV"\n\
echo "   - VTuber Endpoint: $VTUBER_ENDPOINT_URL"\n\
echo "   - Log Level: $LOG_LEVEL"\n\
\n\
# Extract database connection details\n\
DB_HOST=$(echo $DATABASE_URL | sed -n "s/.*@\\([^:]*\\):.*/\\1/p")\n\
DB_PORT=$(echo $DATABASE_URL | sed -n "s/.*:\\([0-9]*\\)\\/.*/\\1/p")\n\
DB_NAME=$(echo $DATABASE_URL | sed -n "s/.*\\/\\([^?]*\\).*/\\1/p")\n\
DB_USER=$(echo $DATABASE_URL | sed -n "s/.*:\\/\\/\\([^:]*\\):.*/\\1/p")\n\
\n\
echo "🔍 Database Connection Details:"\n\
echo "   - Host: $DB_HOST"\n\
echo "   - Port: $DB_PORT"\n\
echo "   - Database: $DB_NAME"\n\
echo "   - User: $DB_USER"\n\
\n\
# Test database connectivity\n\
echo "🔗 Testing database connectivity..."\n\
MAX_ATTEMPTS=30\n\
ATTEMPT=0\n\
\n\
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do\n\
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then\n\
        echo "✅ Database connection successful!"\n\
        break\n\
    fi\n\
    \n\
    echo "⏳ Waiting for database... (attempt $((ATTEMPT + 1))/$MAX_ATTEMPTS)"\n\
    sleep 2\n\
    ATTEMPT=$((ATTEMPT + 1))\n\
done\n\
\n\
if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then\n\
    echo "❌ Database connection failed after $MAX_ATTEMPTS attempts"\n\
    echo "🔧 Troubleshooting information:"\n\
    echo "   - Check if PostgreSQL container is running"\n\
    echo "   - Verify network connectivity"\n\
    echo "   - Confirm database credentials"\n\
    exit 1\n\
fi\n\
\n\
echo "🎯 Starting autonomous agent application..."\n\
exec "$@"\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["npx", "elizaos", "start"] 