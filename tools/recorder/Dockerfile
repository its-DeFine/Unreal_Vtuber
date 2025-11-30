FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gstreamer1.0-tools \
      gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-bad \
      gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav \
      gir1.2-gst-1.0 \
      gir1.2-gst-plugins-bad-1.0 \
      gir1.2-glib-2.0 \
      libgirepository1.0-dev \
      libcairo2-dev \
      libgdk-pixbuf-2.0-dev \
      libpango1.0-dev \
      curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/embody/recorder

COPY control_server.py gs_webrtc_recorder.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8889

CMD ["python3", "/opt/embody/recorder/control_server.py"]
