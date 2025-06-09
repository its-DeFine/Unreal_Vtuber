FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir cognee uvicorn fastapi
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "cognee.api.client:app", "--host", "0.0.0.0", "--port", "8000"]
