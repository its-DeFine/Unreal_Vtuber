# Debian (trixie) ships PyGObject (python3-gi) built for the system Python
# (currently CPython 3.13). Use a matching Python base to avoid ABI mismatch.
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
# Make apt-installed modules (python3-gi) importable from the Python.org runtime (/usr/local).
ENV PYTHONPATH=/usr/lib/python3/dist-packages

# Keep parity with the recorder image dependencies (webrtcbin, rtmpsink, AAC encoders).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-gi \
      python3-gi-cairo \
      ffmpeg \
      gstreamer1.0-tools \
      gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-bad \
      gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav \
      gstreamer1.0-nice \
      gir1.2-gst-1.0 \
      gir1.2-gst-plugins-bad-1.0 \
      gir1.2-glib-2.0 \
      gobject-introspection \
      libgirepository1.0-dev \
      libcairo2-dev \
      libgdk-pixbuf-2.0-dev \
      libpango1.0-dev \
      curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/embody/rtmp-bridge

COPY gs_webrtc_rtmp.py entrypoint.sh requirements.txt ./

RUN chmod +x /opt/embody/rtmp-bridge/entrypoint.sh && \
    pip install --no-cache-dir -r /opt/embody/rtmp-bridge/requirements.txt

CMD ["/opt/embody/rtmp-bridge/entrypoint.sh"]
