FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi httpx uvicorn --no-cache-dir

COPY proxy.py .

CMD ["sh", "-c", "uvicorn proxy:app --host 0.0.0.0 --port $PORT"]
