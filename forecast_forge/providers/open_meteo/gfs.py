"""NOAA GFS (Global Forecast System) model adapter for Open-Meteo."""

from forecast_forge.providers.open_meteo.base_adapter import OpenMeteoBaseAdapter


class NOAAGFSProvider(OpenMeteoBaseAdapter):
    """Adapter for NOAA GFS forecast via Open-Meteo."""

    @property
    def model_name(self) -> str:
        return self.settings.gfs_model
