FROM nvidia/opengl:1.2-glvnd-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV UE_APP_ROOT=/opt/embody

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      xvfb \
      x11-xserver-utils \
      libx11-6 \
      libxrandr2 \
      libxinerama1 \
      libxcursor1 \
      libxi6 \
      libsm6 \
      libglu1-mesa \
      libvulkan1 \
      libpulse0 \
      libdbus-1-3 \
      libfontconfig1 \
      libasound2 \
      netcat \
      curl \
      xdg-user-dirs \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

RUN useradd -m -d /home/embody -s /bin/bash embody && mkdir -p ${UE_APP_ROOT}

COPY docker/pixel-streaming/game/start-embody.sh /usr/local/bin/start-embody.sh
RUN chmod +x /usr/local/bin/start-embody.sh

WORKDIR ${UE_APP_ROOT}

# The build pipeline copies the packaged build into linux-pixel-streaming/ before invoking docker build.
# Use COPY --chown to avoid a second "chown -R" layer that would double the image size.
COPY --chown=embody:embody linux-pixel-streaming/ ${UE_APP_ROOT}/

# Ensure the main launchers are executable (avoid chmod -R to prevent large metadata layers).
RUN chmod +x ${UE_APP_ROOT}/Embody.sh || true && \
    chmod +x ${UE_APP_ROOT}/Embody/Binaries/Linux/Embody-Linux-Shipping || true

ENV UE_PIXEL_STREAMING_ROOT=${UE_APP_ROOT}
ENV USE_XVFB=1
ENV DISPLAY=:99
ENV XVFB_RESOLUTION=1920x1080x24
ENV ULIMIT_NOFILE=1048576

EXPOSE 7777 9877

USER embody
ENTRYPOINT ["/usr/local/bin/start-embody.sh"]
