"""YouTube publishing adapter with OAuth-based user authorization."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..config import (
    UPLOAD_DIR,
    YOUTUBE_DEFAULT_PRIVACY_STATUS,
    YOUTUBE_OAUTH_STATE_PATH,
    YOUTUBE_PROFILE_PATH,
    YOUTUBE_TOKEN_PATH,
)
from ..runtime import (
    get_google_oauth_client_id,
    get_google_oauth_client_secret,
)
from .base import (
    PublishAuthorizationError,
    PublishConfigurationError,
    PublishResult,
    PublishTemporaryError,
)

logger = logging.getLogger(__name__)


class YouTubePublisher:
    """Provider adapter for YouTube uploads."""

    key = "youtube"
    name = "YouTube"
    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    allowed_extensions = {
        ".3gpp",
        ".avi",
        ".flv",
        ".hevc",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".mts",
        ".mxf",
        ".webm",
        ".wmv",
    }
    privacy_values = {"private", "public", "unlisted"}

    def dependencies_installed(self) -> bool:
        try:
            import googleapiclient  # noqa: F401
            import google_auth_oauthlib  # noqa: F401
            import google.oauth2.credentials  # noqa: F401
            return True
        except Exception:
            return False

    def is_configured(self) -> bool:
        return bool(get_google_oauth_client_id() and get_google_oauth_client_secret() and self.dependencies_installed())

    def missing_configuration_message(self) -> str:
        if not self.dependencies_installed():
            return (
                "YouTube publishing dependencies are not installed. Install "
                "`google-api-python-client`, `google-auth-oauthlib`, and related Google auth packages."
            )
        missing: list[str] = []
        if not get_google_oauth_client_id():
            missing.append("GOOGLE_CLIENT_ID")
        if not get_google_oauth_client_secret():
            missing.append("GOOGLE_CLIENT_SECRET")
        if missing:
            return "Save Google OAuth credentials in Settings or set " + ", ".join(missing) + " to enable YouTube publishing."
        return ""

    def get_connection_status(self, redirect_uri: str | None = None) -> dict[str, Any]:
        profile = self._read_json(YOUTUBE_PROFILE_PATH) or {}
        status = {
            "provider": self.key,
            "name": self.name,
            "available": self.is_configured(),
            "configured": bool(get_google_oauth_client_id() and get_google_oauth_client_secret()),
            "dependencies_installed": self.dependencies_installed(),
            "connected": False,
            "channel_id": profile.get("channel_id"),
            "channel_title": profile.get("channel_title"),
            "redirect_uri": redirect_uri,
            "message": "",
        }
        if not status["available"]:
            status["message"] = self.missing_configuration_message()
            return status

        try:
            creds = self._load_credentials()
        except PublishAuthorizationError as exc:
            status["message"] = str(exc)
            return status

        status["connected"] = bool(getattr(creds, "valid", False))
        if not status["channel_title"]:
            try:
                profile = self.refresh_profile()
                status["channel_id"] = profile.get("channel_id")
                status["channel_title"] = profile.get("channel_title")
            except Exception as exc:  # pragma: no cover - best effort metadata
                logger.warning("Unable to refresh YouTube profile metadata: %s", exc)
        return status

    def begin_authorization(self, redirect_uri: str) -> str:
        if not self.is_configured():
            raise PublishConfigurationError(self.missing_configuration_message())

        flow = self._build_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        self._write_json(
            YOUTUBE_OAUTH_STATE_PATH,
            {
                "state": state,
                "redirect_uri": redirect_uri,
            },
        )
        return authorization_url

    def complete_authorization(self, redirect_uri: str, state: str, code: str) -> dict[str, Any]:
        if not self.is_configured():
            raise PublishConfigurationError(self.missing_configuration_message())

        expected = self._read_json(YOUTUBE_OAUTH_STATE_PATH) or {}
        expected_state = expected.get("state")
        if not expected_state or state != expected_state:
            raise PublishAuthorizationError("Invalid YouTube OAuth state. Start the connection flow again.")

        flow = self._build_flow(expected.get("redirect_uri") or redirect_uri)
        try:
            flow.fetch_token(code=code)
        except Exception as exc:
            raise PublishAuthorizationError(f"YouTube authorization failed: {exc}") from exc

        creds = flow.credentials
        if not getattr(creds, "refresh_token", None):
            raise PublishAuthorizationError(
                "YouTube authorization did not return a refresh token. Reconnect and approve offline access."
            )
        self._save_credentials(creds)
        profile = self.refresh_profile()
        if YOUTUBE_OAUTH_STATE_PATH.exists():
            YOUTUBE_OAUTH_STATE_PATH.unlink()
        return profile

    def disconnect(self) -> None:
        for path in (YOUTUBE_TOKEN_PATH, YOUTUBE_PROFILE_PATH, YOUTUBE_OAUTH_STATE_PATH):
            if path.exists():
                path.unlink()

    def refresh_profile(self) -> dict[str, Any]:
        youtube = self._build_client()
        try:
            response = youtube.channels().list(part="snippet", mine=True).execute()
        except Exception as exc:
            raise PublishAuthorizationError(f"Unable to load YouTube account details: {exc}") from exc

        items = response.get("items", [])
        profile = {
            "channel_id": None,
            "channel_title": None,
        }
        if items:
            item = items[0]
            profile["channel_id"] = item.get("id")
            profile["channel_title"] = item.get("snippet", {}).get("title")
        self._write_json(YOUTUBE_PROFILE_PATH, profile)
        return profile

    def publish(self, record: dict[str, Any], job: dict[str, Any]) -> PublishResult:
        if not self.is_configured():
            raise PublishConfigurationError(self.missing_configuration_message())

        source_path = self._resolve_source_path(record)
        youtube = self._build_client()
        title = (job.get("title") or record.get("selected_title") or record.get("filename") or "Untitled episode").strip()
        description = (
            job.get("description")
            or record.get("long_description")
            or record.get("short_description")
            or "Published by Clipmato."
        )
        privacy_status = (job.get("privacy_status") or YOUTUBE_DEFAULT_PRIVACY_STATUS).strip().lower()
        if privacy_status not in self.privacy_values:
            privacy_status = YOUTUBE_DEFAULT_PRIVACY_STATUS

        body = {
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": privacy_status,
            },
        }
        logger.info("Uploading record %s to YouTube from %s", record.get("id"), source_path)

        try:
            from googleapiclient.http import MediaFileUpload

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(str(source_path), chunksize=-1, resumable=True),
            )
            response = None
            while response is None:
                _, response = request.next_chunk()
        except Exception as exc:
            self._raise_publish_error(exc)

        video_id = response.get("id")
        if not video_id:
            raise PublishTemporaryError("YouTube upload completed without returning a video ID.")
        return PublishResult(
            remote_id=video_id,
            remote_url=f"https://www.youtube.com/watch?v={video_id}",
            metadata={
                "title": title,
                "description": description,
                "privacy_status": privacy_status,
            },
        )

    def _resolve_source_path(self, record: dict[str, Any]) -> Path:
        candidates: list[str] = []
        unsupported_path: Path | None = None
        if record.get("edited_audio"):
            candidates.append(str(record["edited_audio"]))
        if record.get("filename"):
            candidates.append(str(UPLOAD_DIR / record["filename"]))
        for candidate in candidates:
            path = Path(candidate).expanduser()
            if path.exists():
                if path.suffix.lower() not in self.allowed_extensions:
                    unsupported_path = path
                    continue
                return path
        if unsupported_path is not None:
            raise PublishConfigurationError(
                "YouTube publishing currently requires a video file. "
                "Upload a video asset or add a render step before publishing."
            )
        raise PublishConfigurationError("The source media for this record is no longer available.")

    def _build_flow(self, redirect_uri: str):
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": get_google_oauth_client_id(),
                    "client_secret": get_google_oauth_client_secret(),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=self.scopes,
        )
        flow.redirect_uri = redirect_uri
        return flow

    def _build_client(self):
        from googleapiclient.discovery import build

        return build("youtube", "v3", credentials=self._load_credentials(), cache_discovery=False)

    def _load_credentials(self):
        if not YOUTUBE_TOKEN_PATH.exists():
            raise PublishAuthorizationError("YouTube is not connected. Connect an account before publishing.")

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        data = self._read_json(YOUTUBE_TOKEN_PATH)
        if not data:
            raise PublishAuthorizationError("YouTube credentials are missing. Connect the account again.")

        creds = Credentials.from_authorized_user_info(data, scopes=self.scopes)
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                raise PublishAuthorizationError(
                    "YouTube authorization has expired or been revoked. Reconnect the account."
                ) from exc
            self._save_credentials(creds)

        if not creds.valid:
            raise PublishAuthorizationError("YouTube authorization is invalid. Reconnect the account.")
        return creds

    def _save_credentials(self, credentials) -> None:
        YOUTUBE_TOKEN_PATH.write_text(credentials.to_json())

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2))

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _raise_publish_error(self, exc: Exception) -> None:
        try:
            from googleapiclient.errors import HttpError
        except Exception:  # pragma: no cover - only hit when dependency is absent
            HttpError = tuple()  # type: ignore[assignment]

        if HttpError and isinstance(exc, HttpError):
            status = getattr(getattr(exc, "resp", None), "status", None)
            details = ""
            content = getattr(exc, "content", b"")
            if content:
                try:
                    payload = json.loads(content.decode("utf-8"))
                    details = payload.get("error", {}).get("message", "")
                except Exception:
                    details = content.decode("utf-8", errors="ignore")
            message = details or str(exc)
            if status in {401, 403}:
                raise PublishAuthorizationError(message) from exc
            if status in {429, 500, 502, 503, 504}:
                raise PublishTemporaryError(message) from exc
            raise PublishConfigurationError(message) from exc

        if isinstance(exc, OSError):
            raise PublishConfigurationError(str(exc)) from exc
        raise PublishTemporaryError(str(exc)) from exc
