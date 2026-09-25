"""Validation layer for provider data quality and physical sanity."""

from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.models import ForecastPoint, Location
from forecast_forge.validation.bounds import (
    BOUND_PRECIPITATION,
    BOUND_RELATIVE_HUMIDITY_2M,
    BOUND_TEMPERATURE_2M,
    BOUND_WIND_SPEED_10M,
)


class ForecastValidator:
    """Validates weather forecast data points against physical realism and schema constraints."""

    @staticmethod
    def validate_location(location: Location) -> bool:
        """Verify that coordinates are valid geographic values."""
        return -90.0 <= location.latitude <= 90.0 and -180.0 <= location.longitude <= 180.0

    @classmethod
    def validate_point(
        cls,
        point: ForecastPoint,
        requested_variables: list[WeatherVariable] | None = None,
    ) -> tuple[bool, int]:
        """Validate a single ForecastPoint.

        Returns:
            Tuple of (is_valid_point, missing_variables_count).
            A point is considered valid if at least one variable is validly populated
            and no populated variable violates physical bounds.
        """
        if requested_variables is None:
            requested_variables = [
                WeatherVariable.TEMPERATURE_2M,
                WeatherVariable.RELATIVE_HUMIDITY_2M,
                WeatherVariable.PRECIPITATION,
                WeatherVariable.WIND_SPEED_10M,
            ]

        missing_count = 0
        has_any_valid_variable = False

        # Validate temperature
        if WeatherVariable.TEMPERATURE_2M in requested_variables:
            if point.temperature_2m is None:
                missing_count += 1
            elif not BOUND_TEMPERATURE_2M.is_valid(point.temperature_2m):
                return False, missing_count
            else:
                has_any_valid_variable = True

        # Validate humidity
        if WeatherVariable.RELATIVE_HUMIDITY_2M in requested_variables:
            if point.relative_humidity_2m is None:
                missing_count += 1
            elif not BOUND_RELATIVE_HUMIDITY_2M.is_valid(point.relative_humidity_2m):
                return False, missing_count
            else:
                has_any_valid_variable = True

        # Validate precipitation
        if WeatherVariable.PRECIPITATION in requested_variables:
            if point.precipitation is None:
                missing_count += 1
            elif not BOUND_PRECIPITATION.is_valid(point.precipitation):
                return False, missing_count
            else:
                has_any_valid_variable = True

        # Validate wind speed
        if WeatherVariable.WIND_SPEED_10M in requested_variables:
            if point.wind_speed_10m is None:
                missing_count += 1
            elif not BOUND_WIND_SPEED_10M.is_valid(point.wind_speed_10m):
                return False, missing_count
            else:
                has_any_valid_variable = True

        return has_any_valid_variable, missing_count

    @classmethod
    def assess_dataset_status(
        cls,
        records: list[ForecastPoint],
        requested_variables: list[WeatherVariable],
    ) -> tuple[ProviderStatus, int, int]:
        """Assess overall status and counts for a dataset.

        Returns:
            Tuple of (status, valid_records_count, missing_variables_count).

        Status semantics:
            AVAILABLE     — HTTP success + all records have valid values for all requested vars.
            DEGRADED      — HTTP success + some records valid, some missing/partial fields.
            NO_VALID_DATA — HTTP success + provider responded but zero usable values exist.
            UNAVAILABLE   — Network error, timeout, HTTP error, or empty response body (no records).
        """
        if not records:
            # No records returned from a successful HTTP 200 response means the provider
            # responded but had nothing. Distinguish from network error by using NO_VALID_DATA
            # only if called from _parse_response (records were built but empty).
            # When called from exception handlers, UNAVAILABLE is set directly.
            return ProviderStatus.NO_VALID_DATA, 0, 0

        valid_records_count = 0
        total_missing_vars = 0

        for record in records:
            is_valid, missing_vars = cls.validate_point(record, requested_variables)
            if is_valid:
                valid_records_count += 1
            total_missing_vars += missing_vars

        # If zero records have valid populated variables (all null or out of bounds)
        if valid_records_count == 0:
            return ProviderStatus.NO_VALID_DATA, 0, total_missing_vars

        # If all records are valid and there are no missing variables → fully AVAILABLE
        if valid_records_count == len(records) and total_missing_vars == 0:
            return ProviderStatus.AVAILABLE, valid_records_count, total_missing_vars

        # Some records valid, some missing/partial → DEGRADED (not UNAVAILABLE)
        return ProviderStatus.DEGRADED, valid_records_count, total_missing_vars
