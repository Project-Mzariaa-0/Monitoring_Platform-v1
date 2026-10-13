from __future__ import annotations

import logging
import os
import time
import uuid

import httpx

logger = logging.getLogger(__name__)


def _create_client(ingest_url: str, ingest_token: str) -> httpx.Client:
    kwargs: dict = {"timeout": 10.0}
    if ingest_url.startswith("http://"):
        kwargs["verify"] = False
    elif os.environ.get("SSL_CERT_FILE") and not os.path.isfile(os.environ["SSL_CERT_FILE"]):
        import certifi
        kwargs["verify"] = certifi.where()
    return httpx.Client(**kwargs)


class EventPublisher:
    def __init__(self, ingest_url: str, ingest_token: str, request_id: str | None = None):
        self.ingest_url = ingest_url
        self.ingest_token = ingest_token
        self._client = _create_client(ingest_url, ingest_token)
        self._client.headers["Authorization"] = f"Bearer {ingest_token}"
        self.request_id = request_id or str(uuid.uuid4())
        self._client.headers["X-Request-ID"] = self.request_id
        logger.info("EventPublisher initialized: url=%s", ingest_url, extra={"session_id": "unknown"})

    def publish(self, event: dict) -> None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.post(self.ingest_url, json=event)
                response.raise_for_status()
                logger.debug(
                    "Published event",
                    extra={"session_id": event.get("session_id"), "event_type": event.get("event_type")},
                )
                return
            except httpx.HTTPStatusError as error:
                status = error.response.status_code if error.response is not None else None
                body = error.response.text[:500] if error.response is not None else ""
                if status is not None and 400 <= status < 500:
                    # Validation/auth errors will never succeed on retry; drop
                    # immediately with the server message so the cause is visible.
                    logger.error(
                        "Dropping event: ingest rejected it (%s %s) (url=%s)",
                        status, body, self.ingest_url,
                        extra={"session_id": event.get("session_id"), "event_type": event.get("event_type")},
                    )
                    return
                last_error = error
                logger.warning(
                    "Publish attempt failed: %s (url=%s)", error, self.ingest_url,
                    extra={"session_id": event.get("session_id"), "event_type": event.get("event_type"), "attempt": attempt + 1},
                )
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
            except Exception as error:
                last_error = error
                logger.warning(
                    "Publish attempt failed: %s (url=%s)", error, self.ingest_url,
                    extra={"session_id": event.get("session_id"), "event_type": event.get("event_type"), "attempt": attempt + 1},
                )
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))

        logger.error("Failed to publish event after 3 attempts, dropping event: %s", last_error)

    def close(self) -> None:
        self._client.close()
