FROM python:3.12-slim

# Build with --build-arg APP_VERSION=v2 to tell two images apart in the canary and rolling-update demos.
ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    APP_VERSION=${APP_VERSION}

WORKDIR /srv

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt \
    && useradd --no-create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY app/ app/

USER 10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/healthz', timeout=2)"]

CMD ["python", "-m", "app.server"]
