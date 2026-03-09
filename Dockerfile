FROM python:3.12-slim

ARG INSTALL_LOCAL_WHISPER=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CLIPMATO_DATA_DIR=/data \
    CLIPMATO_TRANSCRIPTION_BACKEND=openai \
    CLIPMATO_CONTENT_BACKEND=auto \
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

RUN pip install --upgrade pip \
    && if [ "$INSTALL_LOCAL_WHISPER" = "true" ]; then pip install '.[local-transcription]'; else pip install .; fi

RUN groupadd --system clipmato \
    && useradd --system --gid clipmato --create-home --shell /usr/sbin/nologin clipmato \
    && mkdir -p /data \
    && chown -R clipmato:clipmato /data

USER clipmato

EXPOSE 8000
VOLUME ["/data"]

CMD ["clipmato-web"]
