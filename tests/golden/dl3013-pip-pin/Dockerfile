FROM python:3.12-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir flask
USER 10001
CMD ["python", "-m", "flask", "run"]
