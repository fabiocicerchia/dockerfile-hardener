FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir build==1.2.2

FROM python:latest
COPY --from=builder /app /app
USER 10001
CMD ["python", "/app/main.py"]
