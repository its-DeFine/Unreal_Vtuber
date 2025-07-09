FROM python:3.11-slim
WORKDIR /app
COPY autogen_agent ./autogen_agent
COPY static ./static
COPY requirements.txt ./requirements.txt
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --upgrade pip && pip install --no-cache-dir --timeout 1000 -r requirements.txt
CMD ["python", "-m", "autogen_agent.main"]
