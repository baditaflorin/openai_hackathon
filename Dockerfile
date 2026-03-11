FROM python:3.12-slim

ARG INSTALL_LOCAL_WHISPER=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CLIPMATO_DATA_DIR=/data \
    XDG_CACHE_HOME=/data/.cache \
    TORCH_HOME=/data/.cache/torch \
    CLIPMATO_TRANSCRIPTION_BACKEND=local-whisper \
    CLIPMATO_CONTENT_BACKEND=ollama \
    CLIPMATO_OLLAMA_BASE_URL=http://ollama:11434 \
    CLIPMATO_OLLAMA_MODEL=gpt-oss:20b \
    CLIPMATO_OLLAMA_TIMEOUT_SECONDS=120 \
    CLIPMATO_BASE_URL=http://localhost:8000 \
    CLIPMATO_PUBLISH_POLL_SECONDS=15 \
    CLIPMATO_PUBLISH_MAX_ATTEMPTS=3 \
    CLIPMATO_PUBLISH_RETRY_SECONDS=300 \
    CLIPMATO_YOUTUBE_PRIVACY_STATUS=private \
    CLIPMATO_HOST=0.0.0.0 \
    CLIPMATO_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements.txt LICENSE /app/
COPY clipmato /app/clipmato
COPY docker/entrypoint.sh /app/docker/entrypoint.sh

RUN pip install --upgrade pip \
    && if [ "$INSTALL_LOCAL_WHISPER" = "true" ]; then pip install '.[local-transcription]'; else pip install .; fi

RUN chmod +x /app/docker/entrypoint.sh

RUN groupadd --system clipmato \
    && useradd --system --gid clipmato --create-home --shell /usr/sbin/nologin clipmato \
    && mkdir -p /data /data/.cache /data/.cache/torch \
    && chown -R clipmato:clipmato /data

USER clipmato

EXPOSE 8000
VOLUME ["/data"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["clipmato-web"]
