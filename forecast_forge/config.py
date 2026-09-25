"""Configuration management for Forecast Forge AI using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production", "testing"] = Field(
        default="development",
        description="Execution environment tier",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application logging level",
    )
    open_meteo_base_url: str = Field(
        default="https://api.open-meteo.com/v1",
        description="Base URL for Open-Meteo API requests",
    )
    open_meteo_archive_url: str = Field(
        default="https://archive-api.open-meteo.com/v1",
        description="Base URL for Open-Meteo ERA5 archive API requests",
    )
    open_meteo_ensemble_url: str = Field(
        default="https://ensemble-api.open-meteo.com/v1",
        description="Base URL for Open-Meteo ensemble API requests",
    )
    ifs_model: str = Field(
        default="ecmwf_ifs025",
        description="Model identifier for ECMWF IFS in Open-Meteo",
    )
    gfs_model: str = Field(
        default="gfs_seamless",
        description="Model identifier for NOAA GFS in Open-Meteo",
    )
    aifs_model: str = Field(
        default="ecmwf_aifs025",
        description="Model identifier for ECMWF AIFS in Open-Meteo",
    )
    forecast_days: int = Field(
        default=3,
        ge=1,
        le=16,
        description="Default number of forecast days to request",
    )
    http_timeout_seconds: float = Field(
        default=10.0,
        gt=0.0,
        description="HTTP request timeout in seconds",
    )
    http_max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for transient HTTP failures",
    )
    http_backoff_factor: float = Field(
        default=0.5,
        ge=0.0,
        description="Exponential backoff multiplier for HTTP retries",
    )
    nvidia_api_key: str | None = Field(
        default=None,
        description="API Key for NVIDIA Nemotron",
    )
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Base URL for NVIDIA API requests",
    )
    nvidia_model: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b",
        description="NVIDIA model name",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
