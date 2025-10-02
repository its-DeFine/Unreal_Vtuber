FROM python:3.11-slim

WORKDIR /app

COPY stream_recorder/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY stream_recorder /app/stream_recorder
COPY scripts /app/scripts

ENV PYTHONUNBUFFERED=1
EXPOSE 9001

CMD ["python", "-m", "stream_recorder.manager"]
