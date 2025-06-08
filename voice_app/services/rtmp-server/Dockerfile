# Nginx-RTMP Server with GStreamer Support
# Optimized for real-time voice streaming with low latency
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV NGINX_VERSION=1.24.0
ENV RTMP_MODULE_VERSION=1.2.2
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    unzip \
    libpcre3-dev \
    libssl-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev \
    libgd-dev \
    libgeoip-dev \
    liblua5.1-dev \
    lua5.1 \
    libmaxminddb-dev \
    # GStreamer dependencies
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-alsa \
    gstreamer1.0-pulseaudio \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    # Python for processing scripts
    python3 \
    python3-pip \
    python3-dev \
    # Audio/Video libraries
    ffmpeg \
    pulseaudio \
    alsa-utils \
    # Additional utilities
    htop \
    nano \
    curl \
    net-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for processing
RUN pip3 install --no-cache-dir \
    aiohttp \
    asyncio \
    websockets \
    numpy \
    scipy \
    librosa \
    soundfile \
    requests \
    python-multipart \
    pydantic \
    fastapi \
    uvicorn

# Create user for nginx
RUN groupadd -r nginx && useradd -r -g nginx nginx

# Create directories
RUN mkdir -p \
    /var/log/nginx \
    /var/cache/nginx \
    /etc/nginx/conf.d \
    /var/www/html \
    /var/recordings \
    /var/recordings/voice \
    /tmp/hls \
    /tmp/hls/voice \
    /tmp/hls/test \
    /tmp/dash \
    /usr/local/bin \
    /etc/nginx

# Download and compile nginx with RTMP module
WORKDIR /tmp

# Download nginx source
RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
    tar -zxf nginx-${NGINX_VERSION}.tar.gz

# Download nginx-rtmp-module
RUN wget https://github.com/arut/nginx-rtmp-module/archive/v${RTMP_MODULE_VERSION}.tar.gz && \
    tar -zxf v${RTMP_MODULE_VERSION}.tar.gz

# Configure and compile nginx with RTMP module
WORKDIR /tmp/nginx-${NGINX_VERSION}
RUN ./configure \
    --prefix=/etc/nginx \
    --sbin-path=/usr/sbin/nginx \
    --modules-path=/usr/lib/nginx/modules \
    --conf-path=/etc/nginx/nginx.conf \
    --error-log-path=/var/log/nginx/error.log \
    --http-log-path=/var/log/nginx/access.log \
    --pid-path=/var/run/nginx.pid \
    --lock-path=/var/run/nginx.lock \
    --http-client-body-temp-path=/var/cache/nginx/client_temp \
    --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
    --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
    --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
    --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
    --user=nginx \
    --group=nginx \
    --with-compat \
    --with-file-aio \
    --with-threads \
    --with-http_addition_module \
    --with-http_auth_request_module \
    --with-http_dav_module \
    --with-http_flv_module \
    --with-http_gunzip_module \
    --with-http_gzip_static_module \
    --with-http_mp4_module \
    --with-http_random_index_module \
    --with-http_realip_module \
    --with-http_secure_link_module \
    --with-http_slice_module \
    --with-http_ssl_module \
    --with-http_stub_status_module \
    --with-http_sub_module \
    --with-http_v2_module \
    --with-mail \
    --with-mail_ssl_module \
    --with-stream \
    --with-stream_realip_module \
    --with-stream_ssl_module \
    --with-stream_ssl_preread_module \
    --add-module=../nginx-rtmp-module-${RTMP_MODULE_VERSION} \
    && make -j$(nproc) \
    && make install

# Create nginx cache directories
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp

# Set ownership
RUN chown -R nginx:nginx /var/cache/nginx \
                        /var/log/nginx \
                        /var/recordings \
                        /tmp/hls \
                        /tmp/dash \
                        /var/www

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY stat.xsl /etc/nginx/stat.xsl

# Copy processing scripts
COPY scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*.py /usr/local/bin/*.sh

# Copy HTML player files
COPY www/ /var/www/html/

# Create systemd-like init script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Health check script
COPY health_check.sh /usr/local/bin/health_check.sh
RUN chmod +x /usr/local/bin/health_check.sh

# Create password file for recordings (change in production)
RUN echo "admin:$(openssl passwd -apr1 'admin123')" > /etc/nginx/.htpasswd

# Clean up build dependencies and temporary files
RUN apt-get remove -y \
    build-essential \
    wget \
    git \
    && apt-get autoremove -y \
    && rm -rf /tmp/* \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for convenience
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

# Test nginx configuration
RUN nginx -t

# Expose ports
EXPOSE 1935 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health_check.sh

# Start nginx
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"] 