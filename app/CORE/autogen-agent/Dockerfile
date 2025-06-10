FROM python:3.11-slim
WORKDIR /app
COPY autogen_agent ./autogen_agent
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "autogen_agent.main"]
