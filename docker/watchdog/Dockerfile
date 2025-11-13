FROM alpine:3.20

ARG COMPOSE_VERSION=2.27.0

RUN apk add --no-cache ca-certificates curl docker-cli tzdata \
 && mkdir -p /usr/libexec/docker/cli-plugins \
 && curl -fL "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
      -o /usr/libexec/docker/cli-plugins/docker-compose \
 && chmod +x /usr/libexec/docker/cli-plugins/docker-compose

WORKDIR /workspace
COPY scripts/vtuber_watchdog.sh /usr/local/bin/vtuber_watchdog.sh

ENTRYPOINT ["vtuber_watchdog.sh"]
