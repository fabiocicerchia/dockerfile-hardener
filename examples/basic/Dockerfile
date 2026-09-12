FROM python:latest

RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://example.com/app.tar.gz | tar -xz -C /opt

COPY entrypoint.sh /entrypoint.sh
COPY app /opt/app

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD gunicorn --bind 0.0.0.0:8000 app:wsgi
