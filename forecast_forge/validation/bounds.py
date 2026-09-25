"""Physical meteorological domain bounds for data sanity verification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NumericalBound:
    """Allowed range for a numerical meteorological variable."""

    min_value: float
    max_value: float
    unit: str

    def is_valid(self, val: float | None) -> bool:
        """Check whether a value falls within valid physical boundaries."""
        if val is None:
            return False
        return self.min_value <= val <= self.max_value


# Standard domain sanity bounds
BOUND_TEMPERATURE_2M = NumericalBound(min_value=-70.0, max_value=65.0, unit="°C")
BOUND_RELATIVE_HUMIDITY_2M = NumericalBound(min_value=0.0, max_value=100.0, unit="%")
BOUND_PRECIPITATION = NumericalBound(min_value=0.0, max_value=500.0, unit="mm")
BOUND_WIND_SPEED_10M = NumericalBound(min_value=0.0, max_value=450.0, unit="km/h")
