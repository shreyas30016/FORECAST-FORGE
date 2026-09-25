"""ECMWF IFS (Integrated Forecasting System) model adapter for Open-Meteo."""

from forecast_forge.providers.open_meteo.base_adapter import OpenMeteoBaseAdapter


class ECMWFIFSProvider(OpenMeteoBaseAdapter):
    """Adapter for ECMWF IFS 0.25° / HRES forecast via Open-Meteo."""

    @property
    def model_name(self) -> str:
        return self.settings.ifs_model
