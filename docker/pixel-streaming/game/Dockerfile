FROM nvidia/opengl:1.2-glvnd-runtime-ubuntu22.04

ENV UE_APP_ROOT=/opt/embody

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libx11-6 \
      libxrandr2 \
      libxinerama1 \
      libxcursor1 \
      libxi6 \
      libsm6 \
      libglu1-mesa \
      libice6 \
      libssl3 \
      libuuid1 \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR ${UE_APP_ROOT}

# The CI workflow copies the packaged build into build/LinuxNoEditor relative to
# the repository root before invoking docker build.
COPY linux-pixel-streaming/ ${UE_APP_ROOT}/

RUN chmod +x ${UE_APP_ROOT}/Engine/Binaries/Linux/* || true && \
    chmod +x ${UE_APP_ROOT}/*.sh || true

ENV LD_LIBRARY_PATH=${UE_APP_ROOT}/Engine/Binaries/Linux:${UE_APP_ROOT}/Engine/Binaries/Linux/PixelStreaming:${LD_LIBRARY_PATH:-}
ENV UE_PIXEL_STREAMING_ROOT=${UE_APP_ROOT}

EXPOSE 7777 9877

ENTRYPOINT ["./LinuxServer.sh"]
