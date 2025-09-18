FROM embody-pixel-streaming:latest

USER root

# Utilities required by Epic's packaged scripts at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

ENV SIGNALING_ROOT=/opt/embody/Embody/Samples/PixelStreaming/WebServers \
    SIGNALING_SCRIPTS=/opt/embody/Embody/Samples/PixelStreaming/WebServers/SignallingWebServer/platform_scripts/bash

WORKDIR ${SIGNALING_SCRIPTS}
RUN chmod +x *.sh \
    && echo "v18.16.1" > ${SIGNALING_ROOT}/NODE_VERSION \
    && ./setup.sh --nosudo --build --deps \
    && PATH="${SIGNALING_SCRIPTS}/node/bin:$PATH" npm install --prefix ${SIGNALING_ROOT}/SignallingWebServer

COPY docker/unreal-streaming/signaling/run-packaged-signaling.sh /usr/local/bin/run-packaged-signaling.sh
RUN chmod +x /usr/local/bin/run-packaged-signaling.sh

EXPOSE 8080 8888 8889

ENV PUBLIC_IP=auto \
    HTTP_PORT=8080 \
    STREAMER_PORT=8888 \
    SFU_PORT=8889 \
    STUN_SERVER=stun.l.google.com:19302 \
    TURN_SERVER= \
    TURN_USER= \
    TURN_PASS= \
    ENABLE_REST_API=0 \
    SIGNALING_EXTRA_ARGS=

ENTRYPOINT ["/usr/local/bin/run-packaged-signaling.sh"]
