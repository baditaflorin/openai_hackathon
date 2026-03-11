#!/usr/bin/env sh
set -eu

# Host-native launch path for macOS/Linux local runs.
# Override these inline or via environment before invoking the script.
: "${CLIPMATO_HOST:=127.0.0.1}"
: "${CLIPMATO_PORT:=8000}"
: "${CLIPMATO_TRANSCRIPTION_BACKEND:=local-whisper}"
: "${CLIPMATO_CONTENT_BACKEND:=ollama}"
: "${CLIPMATO_LOCAL_WHISPER_MODEL:=medium}"
: "${CLIPMATO_LOCAL_WHISPER_DEVICE:=mps}"
: "${CLIPMATO_OLLAMA_BASE_URL:=http://localhost:11434}"
: "${CLIPMATO_OLLAMA_MODEL:=mistral-nemo:12b-instruct-2407-q3_K_S}"

export CLIPMATO_HOST
export CLIPMATO_PORT
export CLIPMATO_TRANSCRIPTION_BACKEND
export CLIPMATO_CONTENT_BACKEND
export CLIPMATO_LOCAL_WHISPER_MODEL
export CLIPMATO_LOCAL_WHISPER_DEVICE
export CLIPMATO_OLLAMA_BASE_URL
export CLIPMATO_OLLAMA_MODEL

exec clipmato-web "$@"
