"""Temporal Model Registry for Scientific Replay."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


class ModelArtifactRecord(BaseModel):
    model_name: str
    artifact_path: str
    artifact_hash: str
    training_start: datetime | None = None
    training_end: datetime | None = None
    created_at: datetime
    feature_schema_version: str | None = None
    model_version: str
    status: str = "ACTIVE"
    evaluation_start: datetime | None = None
    evaluation_end: datetime | None = None
    causal_cutoff: datetime | None = None
    evaluation_mode: str | None = None
    reference_source: str | None = None
    provenance: str | None = None
    feature_set: list[str] | None = None
    threshold_quantile: float | None = None
    thresholds_by_lead: dict[str, float] | None = None


class ReplayModelRegistry:
    """Registry to load and validate model artifacts against a causal cutoff (T0)."""

    def __init__(self, registry_path: str = ".model_cache/registry.json"):
        self.registry_path = Path(registry_path)
        self.records: dict[str, ModelArtifactRecord] = {}
        self._load()

    def _load(self):
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text())
                for item in data.get("artifacts", []):
                    rec = ModelArtifactRecord(**item)
                    self.records[rec.model_name] = rec
            except Exception:
                pass

    def get_valid_artifact(self, model_name: str, t0: datetime) -> ModelArtifactRecord | None:
        """Returns the artifact if it was trained strictly on data prior to T0."""
        rec = self.records.get(model_name)
        if not rec:
            return None

        # We must enforce that the model's training_end is <= T0
        cutoff = rec.causal_cutoff or rec.training_end
        if cutoff:
            # Ensure both are timezone aware for comparison
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=UTC)
            t0_cmp = t0 if t0.tzinfo else t0.replace(tzinfo=UTC)

            if cutoff > t0_cmp:
                return None

        return rec
