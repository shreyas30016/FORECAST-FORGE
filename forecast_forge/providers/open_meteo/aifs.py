"""ECMWF AIFS (Artificial Intelligence Forecasting System) adapter for Open-Meteo."""

from forecast_forge.providers.open_meteo.base_adapter import OpenMeteoBaseAdapter


class ECMWFAIFSProvider(OpenMeteoBaseAdapter):
    """Adapter for ECMWF AIFS 0.25° machine-learning NWP forecast via Open-Meteo.

    Critical Integrity Rules:
    - Never substitute AIFS data with IFS or GFS data.
    - Never impute, backfill, or fabricate missing values.
    - If the provider returns HTTP 200 with all null values, report status as NO_VALID_DATA.
      This does not imply a provider outage; the HTTP exchange succeeded but the requested
      variable values are unusable at this resolution or time window.
    """

    @property
    def model_name(self) -> str:
        return self.settings.aifs_model
