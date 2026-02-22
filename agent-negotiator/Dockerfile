FROM node:22-slim AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY tsconfig.json ./
COPY src/ src/
RUN npm run build

FROM node:22-slim
WORKDIR /app
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /data /config \
    && chown -R appuser:appuser /app /data /config
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev
COPY --from=builder /app/dist dist/

ENV NODE_ENV=production
ENV NEGOTIATOR_PORT=9100
ENV NEGOTIATOR_DATA_DIR=/data
ENV NEGOTIATOR_CONFIG_FILE=/config/negotiator.yaml

USER appuser
EXPOSE 9100

CMD ["node", "dist/index.js"]
