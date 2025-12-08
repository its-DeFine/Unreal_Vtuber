FROM ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest

USER root

# Reset the packaged payload and copy in the new build bytes.
RUN rm -rf /opt/embody && mkdir -p /opt/embody
COPY linux-pixel-streaming/ /opt/embody/

RUN chown -R embody:embody /opt/embody && \
    chmod +x /opt/embody/Engine/Binaries/Linux/* || true && \
    chmod +x /opt/embody/*.sh || true

USER embody
ENV UE_PIXEL_STREAMING_ROOT=/opt/embody
WORKDIR /opt/embody

EXPOSE 7777 9877
