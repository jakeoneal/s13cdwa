FROM ghcr.io/berriai/litellm:main-latest

COPY config.yaml /app/config.yaml

CMD ["sh", "-c", "litellm --config /app/config.yaml --port $PORT --num_workers 1"]
