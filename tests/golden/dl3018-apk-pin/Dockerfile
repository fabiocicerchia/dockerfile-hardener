FROM alpine:3.22 AS builder
RUN apk add --no-cache curl=8.12.1-r1

FROM alpine:3.22
RUN apk add --no-cache curl
USER 10001
CMD ["/usr/local/bin/app"]
