"""Schemas and data models for the evaluation engine."""

from datetime import date

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    """Raw statistical evaluation metrics."""

    mae: float | None = Field(default=None, description="Mean Absolute Error")
    rmse: float | None = Field(default=None, description="Root Mean Square Error")
    mean_bias: float | None = Field(default=None, description="Mean Bias Error")
    valid_samples: int = Field(
        default=0, description="Number of valid paired predictions and observations"
    )
    missing_samples: int = Field(default=0, description="Number of missing or invalid pairs")


class ModelScore(BaseModel):
    """Normalized evaluation score for a model."""

    model: str = Field(description="Model identifier")
    variable: str = Field(description="Weather variable being scored")
    lead_time_bucket: str = Field(description="Configured lead time bucket")
    metrics: MetricResult
    normalized_error: float | None = Field(
        default=None, description="Error normalized against other models in the same bucket"
    )
    reliability_score: float | None = Field(
        default=None, description="0-100 reliability score (higher is better)"
    )
    is_valid: bool = Field(description="Whether the model met minimum sample thresholds")


class WeightResult(BaseModel):
    """Derived weight for a model based on historical reliability."""

    model: str = Field(description="Model identifier")
    variable: str = Field(description="Weather variable being weighted")
    lead_time_bucket: str = Field(description="Configured lead time bucket")
    weight: float = Field(
        ge=0.0, le=1.0, description="Normalized weight summing to 1.0 across models"
    )
    method: str = Field(description="Method used for weighting (e.g., 'inverse_rmse')")


class DataSplitConfig(BaseModel):
    """Chronological split boundaries for ML evaluation/training."""

    train_start: date | None = Field(default=None)
    train_end: date | None = Field(default=None)
    val_start: date | None = Field(default=None)
    val_end: date | None = Field(default=None)
    test_start: date | None = Field(default=None)
    test_end: date | None = Field(default=None)
