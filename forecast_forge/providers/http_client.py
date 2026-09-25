"""Resilient asynchronous HTTP client with bounded retries and exponential backoff."""

import asyncio
import time
from typing import Any

import httpx

from forecast_forge.config import Settings, get_settings
from forecast_forge.core.exceptions import (
    ProviderError,
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)


class ResilientHTTPClient:
    """HTTP client wrapper providing retry policies, timeouts, and structured error mapping."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        provider_name: str = "UnknownProvider",
        model_name: str | None = None,
    ) -> tuple[int, Any, float]:
        """Perform an HTTP GET request with retries on transient errors.

        Returns:
            Tuple of (status_code, json_data, latency_ms).

        Raises:
            ProviderRateLimitError: On HTTP 429.
            ProviderHTTPError: On non-retryable 4xx or persistent 5xx HTTP errors.
            ProviderTimeoutError: If the request exceeds timeout after retries.
            ProviderError: On network connection errors after retries or JSON decode failures.
        """
        timeout = httpx.Timeout(self.settings.http_timeout_seconds)
        attempt = 0
        max_retries = self.settings.http_max_retries
        backoff = self.settings.http_backoff_factor

        start_time = time.perf_counter()

        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params)
                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    status_code = response.status_code

                    # HTTP 429: Rate Limited
                    if status_code == 429:
                        logger.warning(
                            "Provider %s rate-limited request (HTTP 429)",
                            provider_name,
                        )
                        raise ProviderRateLimitError(
                            message=f"Rate limit exceeded (HTTP 429) from {provider_name}",
                            provider_name=provider_name,
                            model_name=model_name,
                        )

                    # HTTP 4xx: Client Error (Do not retry)
                    if 400 <= status_code < 500:
                        logger.warning(
                            "Provider %s client error HTTP %d: %s",
                            provider_name,
                            status_code,
                            response.text[:200],
                        )
                        raise ProviderHTTPError(
                            message=f"HTTP {status_code} client error from {provider_name}",
                            provider_name=provider_name,
                            status_code=status_code,
                            model_name=model_name,
                            response_body=response.text,
                        )

                    # HTTP 5xx: Server Error (Retry if attempts remain)
                    if status_code >= 500:
                        if attempt <= max_retries:
                            sleep_duration = backoff * (2 ** (attempt - 1))
                            logger.warning(
                                "Provider %s HTTP %d on attempt %d/%d; retrying in %.2fs",
                                provider_name,
                                status_code,
                                attempt,
                                max_retries,
                                sleep_duration,
                            )
                            await asyncio.sleep(sleep_duration)
                            continue

                        raise ProviderHTTPError(
                            message=(
                                f"HTTP {status_code} server error from "
                                f"{provider_name} after retries"
                            ),
                            provider_name=provider_name,
                            status_code=status_code,
                            model_name=model_name,
                            response_body=response.text,
                        )

                    # Successful response: Parse JSON
                    try:
                        data = response.json()
                        return status_code, data, latency_ms
                    except Exception as e:
                        logger.error(
                            "Provider %s returned unparseable JSON: %s",
                            provider_name,
                            str(e),
                        )
                        raise ProviderError(
                            message=f"Malformed JSON from {provider_name}: {e}",
                            provider_name=provider_name,
                            model_name=model_name,
                        ) from e

            except httpx.TimeoutException as e:
                if attempt <= max_retries:
                    sleep_duration = backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Timeout querying %s on attempt %d/%d; retrying in %.2fs",
                        provider_name,
                        attempt,
                        max_retries,
                        sleep_duration,
                    )
                    await asyncio.sleep(sleep_duration)
                    continue

                latency_ms = (time.perf_counter() - start_time) * 1000.0
                raise ProviderTimeoutError(
                    message=f"Timeout after {attempt} attempts querying {provider_name}",
                    provider_name=provider_name,
                    model_name=model_name,
                ) from e

            except httpx.RequestError as e:
                # Catch network connection errors
                if attempt <= max_retries:
                    sleep_duration = backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Network error querying %s on attempt %d/%d: %s; retrying in %.2fs",
                        provider_name,
                        attempt,
                        max_retries,
                        str(e),
                        sleep_duration,
                    )
                    await asyncio.sleep(sleep_duration)
                    continue

                latency_ms = (time.perf_counter() - start_time) * 1000.0
                raise ProviderError(
                    message=f"Network error querying {provider_name} after {attempt} attempts: {e}",
                    provider_name=provider_name,
                    model_name=model_name,
                ) from e
