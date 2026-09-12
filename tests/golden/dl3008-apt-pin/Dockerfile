FROM debian:bookworm-slim AS builder
RUN apt-get update \
 && apt-get install --no-install-recommends -y curl=7.88.1-10+deb12u5 \
 && rm -rf /var/lib/apt/lists/*

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install --no-install-recommends -y curl \
 && rm -rf /var/lib/apt/lists/*
USER 10001
CMD ["/usr/local/bin/app"]
