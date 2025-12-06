FROM ghcr.io/its-define/unreal_vtuber/embody-signaling:latest

ENV DEBIAN_FRONTEND=noninteractive

# Base deps: Python + supervisor + GStreamer stack for recorder-control.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 \
      python3-venv \
      python3-pip \
      python3-dev \
      pkg-config \
      sudo \
      supervisor \
      gstreamer1.0-tools \
      gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-bad \
      gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav \
      gstreamer1.0-nice \
      gir1.2-gstreamer-1.0 \
      gir1.2-gst-plugins-base-1.0 \
      gir1.2-gst-plugins-bad-1.0 \
      gir1.2-glib-2.0 \
      libgirepository1.0-dev \
      libcairo2-dev \
      libgdk-pixbuf-2.0-dev \
      libpango1.0-dev \
      curl \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/embody

# Runner + recorder sources.
COPY unreal-script-runner /opt/embody/runner
COPY tools/recorder /opt/embody/recorder

# Shared venv for runner + recorder + facade endpoints.
RUN python3 -m venv /opt/embody/.venv && \
    /opt/embody/.venv/bin/pip install --no-cache-dir \
      -r /opt/embody/runner/requirements.txt \
      -r /opt/embody/recorder/requirements.txt

# Supervisor configuration to launch signaling + runner + recorder-control in one container.
COPY docker/embody-app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ENV PATH="/opt/embody/.venv/bin:${PATH}"
ENV RUNNER_PORT=9877
ENV RECORDER_CTRL_PORT=8889
ENV SIGNALING_HTTP_PORT=80
ENV SIGNALING_STREAMER_PORT=8888
ENV SIGNALING_SFU_PORT=8889
ENV ENABLE_REST_API=1
ENV VTUBER_TCP_HOST=vtuber-unreal-game
ENV VTUBER_TCP_PORT=7777
ENV VTUBER_SESSION_ROOT=/opt/embody/sessions
ENV VTUBER_ALLOWED_ADDRESSES=127.0.0.1,::1
ENV RECORDER_SIGNALING_URL=ws://localhost:80
ENV RECORDER_OUTPUT_DIR=/recordings
ENV RUNNER_URL=http://127.0.0.1:9877
ENV PLANNER_URL=
ENV PLAN_SPEECH_SPACING_MS=2000
ENV RUNNER_POLL_SECONDS=120

EXPOSE 80 8888 8889

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
