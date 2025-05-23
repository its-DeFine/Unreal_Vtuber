FROM node:20-alpine

# Install dependencies required for building native modules
RUN apk add --no-cache python3 make g++ sqlite

# Set working directory
WORKDIR /app

# Install bun globally first
RUN npm install -g bun

# Copy package files first for better caching
COPY package*.json ./
COPY tsconfig*.json ./
COPY tsup.config.ts ./

# Install dependencies
RUN bun install

# Copy source code
COPY src/ ./src/

# Build the TypeScript project
RUN bun run build

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Default command (can be overridden in docker-compose)
CMD ["bun", "run", "start"] 