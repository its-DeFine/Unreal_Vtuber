# webapp/Dockerfile

# Stage 1: Build the React/Vite application
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json and lock file
COPY package.json package-lock.json* ./
# If you use yarn, it would be:
# COPY package.json yarn.lock ./
# If you use pnpm, it would be:
# COPY package.json pnpm-lock.yaml ./


# Install dependencies
RUN npm install --legacy-peer-deps
# Or for yarn: RUN yarn install --frozen-lockfile
# Or for pnpm: RUN pnpm install --frozen-lockfile

# Copy the rest of your webapp's source code
COPY . .

# Build the application (ensure your package.json has this script)
RUN npm run build # This should output to a 'dist' folder by default for Vite

# Stage 2: Serve the built assets with Caddy
FROM caddy:2-alpine

# Copy the Caddyfile from your webapp directory into the image
# This assumes Caddyfile is in the same directory as this Dockerfile (i.e., webapp/Caddyfile)
COPY Caddyfile /etc/caddy/Caddyfile

# Copy the built static assets from the 'builder' stage
# This assumes your build output is in /app/dist within the builder stage
COPY --from=builder /app/dist /srv

# Caddy will automatically serve files from /srv and use /etc/caddy/Caddyfile
# Default Caddy port is 80 unless overridden in Caddyfile or by CMD.
# Your Caddyfile seems to configure Caddy to listen on port 8088.
# If Caddyfile makes Caddy listen on :8088, you might want to EXPOSE 8088.
# Caddy's default command is `caddy run --config /etc/caddy/Caddyfile --adapter caddyfile`
# which is usually sufficient.