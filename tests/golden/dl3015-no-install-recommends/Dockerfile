FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y curl=7.88.1-10+deb12u5 && rm -rf /var/lib/apt/lists/*
USER 10001
CMD ["/usr/local/bin/app"]
