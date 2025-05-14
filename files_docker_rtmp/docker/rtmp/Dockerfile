FROM ubuntu:22.04

# ---------- Build FFmpeg with everything we need ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && \
    apt install -y \
      build-essential yasm pkg-config libssl-dev libx264-dev libfdk-aac-dev \
      libopus-dev libvpx-dev libx265-dev git wget ca-certificates nasm

WORKDIR /opt
RUN git clone --depth 1 https://github.com/FFmpeg/FFmpeg ffmpeg && \
    cd ffmpeg && ./configure --enable-gpl --enable-nonfree \
        --enable-libx264 --enable-libx265 --enable-libvpx \
        --enable-libopus --enable-libfdk-aac \
    && make -j$(nproc) && make install && \
    cd / && rm -rf /opt/ffmpeg  # Clean up build directory

# ---------- Nginx with RTMP ----------
RUN apt install -y nginx-light libnginx-mod-rtmp && \
    apt clean && rm -rf /var/lib/apt/lists/* # Clean up apt cache

RUN mkdir -p /opt/data/hls && chmod -R 777 /opt/data

COPY nginx.conf /etc/nginx/nginx.conf
COPY run_transcode.sh /usr/local/bin/run_transcode.sh
RUN chmod +x /usr/local/bin/run_transcode.sh

# Ensure Nginx logs go to stdout/stderr for Docker
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

EXPOSE 1935 8080
STOPSIGNAL SIGTERM
CMD ["nginx", "-g", "daemon off;"] 