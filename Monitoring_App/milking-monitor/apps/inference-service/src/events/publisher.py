from __future__ import annotations

import logging
import os
import time

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
    def __init__(self, ingest_url: str, ingest_token: str):
        self.ingest_url = ingest_url
        self.ingest_token = ingest_token
        self._client = _create_client(ingest_url, ingest_token)
        self._client.headers["Authorization"] = f"Bearer {ingest_token}"
        logger.info("EventPublisher initialized: url=%s", ingest_url)

    def publish(self, event: dict) -> None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.post(self.ingest_url, json=event)
                response.raise_for_status()
                logger.debug("Published %s event for session %s", event.get("event_type"), event.get("session_id"))
                return
            except Exception as error:
                last_error = error
                logger.warning("Publish attempt %d failed: %s (url=%s)", attempt + 1, error, self.ingest_url)
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))

        logger.error("Failed to publish event after 3 attempts, dropping event: %s", last_error)

    def close(self) -> None:
        self._client.close()
