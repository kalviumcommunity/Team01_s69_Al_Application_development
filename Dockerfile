FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py index.html corpus.json ./
EXPOSE 8080
# Demo credentials are safe only when accessing this container on a loopback port.
# For network binding, set both password env vars at container creation.
CMD ["python", "app.py", "--host", "0.0.0.0"]
