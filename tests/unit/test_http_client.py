"""Unit tests for ResilientHTTPClient retry, timeout, and error handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from forecast_forge.config import Settings
from forecast_forge.core.exceptions import (
    ProviderError,
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from forecast_forge.providers.http_client import ResilientHTTPClient


@pytest.fixture
def fast_settings() -> Settings:
    """Settings with zero backoff for rapid unit testing."""
    return Settings(
        http_timeout_seconds=1.0,
        http_max_retries=2,
        http_backoff_factor=0.0,
    )


@pytest.mark.asyncio
async def test_http_client_success(fast_settings: Settings):
    """Verify HTTP client successfully parses JSON on 200 OK."""
    client = ResilientHTTPClient(settings=fast_settings)
    mock_resp = httpx.Response(
        200, json={"status": "ok"}, request=httpx.Request("GET", "http://test")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        status, data, latency = await client.get_json("http://test", provider_name="TestProvider")

    assert status == 200
    assert data == {"status": "ok"}
    assert latency >= 0.0


@pytest.mark.asyncio
async def test_http_client_429_rate_limit(fast_settings: Settings):
    """Verify HTTP 429 raises ProviderRateLimitError immediately without retry."""
    client = ResilientHTTPClient(settings=fast_settings)
    mock_resp = httpx.Response(
        429, text="Rate limit exceeded", request=httpx.Request("GET", "http://test")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(ProviderRateLimitError):
            await client.get_json("http://test", provider_name="TestProvider")

    # Should only call once, no retries on 429
    assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_http_client_400_client_error(fast_settings: Settings):
    """Verify HTTP 400 raises ProviderHTTPError immediately without retry."""
    client = ResilientHTTPClient(settings=fast_settings)
    mock_resp = httpx.Response(400, text="Bad Request", request=httpx.Request("GET", "http://test"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(ProviderHTTPError) as exc_info:
            await client.get_json("http://test", provider_name="TestProvider")

    assert exc_info.value.status_code == 400
    assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_http_client_500_retries_and_fails(fast_settings: Settings):
    """Verify HTTP 500 retries up to max_retries before raising ProviderHTTPError."""
    client = ResilientHTTPClient(settings=fast_settings)
    mock_resp = httpx.Response(
        500, text="Internal Server Error", request=httpx.Request("GET", "http://test")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(ProviderHTTPError) as exc_info:
            await client.get_json("http://test", provider_name="TestProvider")

    assert exc_info.value.status_code == 500
    # Initial attempt + 2 retries = 3 attempts
    assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_http_client_timeout_retries_and_fails(fast_settings: Settings):
    """Verify timeout retries up to max_retries before raising ProviderTimeoutError."""
    client = ResilientHTTPClient(settings=fast_settings)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ReadTimeout("Timed out")
        with pytest.raises(ProviderTimeoutError):
            await client.get_json("http://test", provider_name="TestProvider")

    assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_http_client_malformed_json(fast_settings: Settings):
    """Verify malformed JSON raises ProviderError."""
    client = ResilientHTTPClient(settings=fast_settings)
    mock_resp = httpx.Response(
        200, text="not valid json", request=httpx.Request("GET", "http://test")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(ProviderError) as exc_info:
            await client.get_json("http://test", provider_name="TestProvider")

    assert "Malformed JSON" in str(exc_info.value)
