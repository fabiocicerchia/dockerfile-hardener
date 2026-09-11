FROM node:20.11-alpine AS builder
RUN node --version

FROM node
COPY --from=builder /app /app
USER 10001
CMD ["node", "/app/index.js"]
