"""Open-Meteo provider adapters for ECMWF IFS, NOAA GFS, and ECMWF AIFS."""

from forecast_forge.providers.open_meteo.aifs import ECMWFAIFSProvider
from forecast_forge.providers.open_meteo.base_adapter import OpenMeteoBaseAdapter
from forecast_forge.providers.open_meteo.gfs import NOAAGFSProvider
from forecast_forge.providers.open_meteo.ifs import ECMWFIFSProvider

__all__ = [
    "OpenMeteoBaseAdapter",
    "ECMWFIFSProvider",
    "NOAAGFSProvider",
    "ECMWFAIFSProvider",
]
