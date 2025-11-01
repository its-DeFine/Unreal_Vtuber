FROM ghcr.io/its-define/unreal_vtuber/embody-signaling:latest

USER root

ENV SIGNALING_ROOT=/opt/embody/Embody/Samples/PixelStreaming/WebServers

RUN rm -rf ${SIGNALING_ROOT}/SignallingWebServer/www \
    && mkdir -p ${SIGNALING_ROOT}/SignallingWebServer/www
COPY CustomizedPixelStreamFrontEnd/SignallingWebServer/www/ ${SIGNALING_ROOT}/SignallingWebServer/www/

RUN chown -R embody:embody ${SIGNALING_ROOT}/SignallingWebServer/www

USER embody
