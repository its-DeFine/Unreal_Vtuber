FROM docker:27-cli

RUN apk add --no-cache python3 iptables

WORKDIR /home/ubuntu/Unreal_Vtuber

COPY agent.py /usr/local/bin/orchestrator-edge-rotator
RUN chmod 755 /usr/local/bin/orchestrator-edge-rotator

CMD ["/usr/local/bin/orchestrator-edge-rotator"]

