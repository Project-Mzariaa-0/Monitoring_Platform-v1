from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, ingest_url: str, ingest_token: str):
        self.ingest_url = ingest_url
        self.ingest_token = ingest_token

    def publish(self, event: dict) -> None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        self.ingest_url,
                        json=event,
                        headers={"Authorization": f"Bearer {self.ingest_token}"},
                    )
                    response.raise_for_status()
                    logger.debug("Published %s event for session %s", event.get("event_type"), event.get("session_id"))
                    return
            except Exception as error:
                last_error = error
                logger.warning("Publish attempt %d failed: %s", attempt + 1, error)

        logger.error("Failed to publish event after 3 attempts, dropping event: %s", last_error)
