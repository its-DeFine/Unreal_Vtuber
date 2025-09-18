FROM node:18-bullseye

ARG PS_BRANCH=UE5.5
ENV PIXEL_STREAMING_BRANCH=${PS_BRANCH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl build-essential python3 xz-utils protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${PIXEL_STREAMING_BRANCH}" https://github.com/EpicGames/PixelStreamingInfrastructure.git /opt/pixel-streaming

WORKDIR /opt/pixel-streaming/SignallingWebServer/platform_scripts/bash
RUN ./setup.sh --nosudo --build --default-stun

WORKDIR /opt/pixel-streaming/SignallingWebServer
COPY start-signaling.sh /usr/local/bin/start-signaling.sh
RUN chmod +x /usr/local/bin/start-signaling.sh

EXPOSE 8080 8888 8889

ENV PUBLIC_IP=auto \
    HTTP_PORT=8080 \
    STREAMER_PORT=8888 \
    SFU_PORT=8889 \
    STUN_SERVER=stun.l.google.com:19302 \
    TURN_SERVER= \
    TURN_USER= \
    TURN_PASS= \
    ENABLE_REST_API=0

CMD ["/usr/local/bin/start-signaling.sh"]
