import json
from datetime import datetime
from pathlib import Path

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.trace.schemas import DecisionTrace


class TraceStorage:
    """JSON-backed storage for Decision Traces."""

    def __init__(self, cache_dir: str = ".trace_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(self, trace: DecisionTrace, replay_id: str | None = None):
        """Save a new DecisionTrace as a JSON file."""
        # For simplicity, store in a file named after the trace_id
        file_path = self.cache_dir / f"{trace.trace_id}.json"

        # We can add replay_id to the JSON if it's not already in the trace.
        # Store it as metadata since the schema doesn't have it directly.
        data = trace.model_dump(mode="json")
        if replay_id:
            data["_replay_id"] = replay_id

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def get_trace(self, trace_id: str) -> DecisionTrace | None:
        """Retrieve a DecisionTrace by its unique ID."""
        file_path = self.cache_dir / f"{trace_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                return DecisionTrace.model_validate(data)
        except Exception:
            return None

    def find_trace(
        self,
        latitude: float,
        longitude: float,
        valid_time: datetime,
        lead_time_hours: int,
        variable: WeatherVariable,
    ) -> DecisionTrace | None:
        """Find a trace by its forecast context."""
        # This is less efficient with JSON files, but works for the scale of local tests
        # In a real app we might use SQLite or index it
        latest_trace = None
        for file_path in self.cache_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Match context
                loc = data.get("location", {})
                ctx = data.get("request_context", {})

                # Loose float comparison
                if abs(loc.get("latitude", 0) - latitude) > 0.001:
                    continue
                if abs(loc.get("longitude", 0) - longitude) > 0.001:
                    continue

                if ctx.get("lead_time_hours") != lead_time_hours:
                    continue
                if ctx.get("variable") != variable.value:
                    continue

                # Check valid time
                vt_str = ctx.get("valid_time")
                if not vt_str:
                    continue
                vt = datetime.fromisoformat(vt_str.replace("Z", "+00:00"))
                if vt != valid_time:
                    continue

                trace = DecisionTrace.model_validate(data)

                if latest_trace is None or trace.created_at > latest_trace.created_at:
                    latest_trace = trace

            except Exception:
                continue

        return latest_trace

    def find_by_replay(self, replay_id: str) -> list[DecisionTrace]:
        """Find all traces associated with a replay ID."""
        traces = []
        for file_path in self.cache_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("_replay_id") == replay_id:
                    traces.append(DecisionTrace.model_validate(data))
            except Exception:
                continue
        # Sort traces by valid time
        traces.sort(key=lambda t: t.request_context.valid_time)
        return traces
