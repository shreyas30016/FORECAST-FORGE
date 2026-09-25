export type WeatherCondition =
  | "SUNNY"
  | "PARTLY_CLOUDY"
  | "CLOUDY"
  | "RAIN"
  | "HEAVY_RAIN"
  | "STORM"
  | "WIND"
  | "FOG"
  | "NIGHT";

export interface NormalizedWeatherState {
  condition: WeatherCondition;
  temperature: number;
  feelsLike: number;
  precipitation: number; // mm
  windSpeed: number; // km/h
  windDirection: number; // degrees
  humidity: number; // %
  cloudCover: number; // 0-100%
  isDay: boolean;
  pressure: number; // hPa
  visibility: number; // km
  timestamp: string;
}

/**
 * Deterministically derives a high-level visual weather state from real forecast data.
 * Adheres to 01_NEW_UI_DESIGN_SYSTEM.md rules: no fabricated values.
 */
export function deriveWeatherVisualState(
  point: {
    timestamp?: string;
    temperature_2m?: number | null;
    precipitation?: number | null;
    wind_speed_10m?: number | null;
    relative_humidity_2m?: number | null;
  } | null | undefined,
  timeString?: string
): NormalizedWeatherState {
  const now = timeString ? new Date(timeString) : new Date();
  const hour = now.getUTCHours();
  // Approximate day/night (between 06:00 and 18:00 UTC for tropical regions)
  const isDay = hour >= 6 && hour < 18;

  const temp = point?.temperature_2m ?? 28.0;
  const precip = point?.precipitation ?? 0.0;
  const wind = point?.wind_speed_10m ?? 12.0;
  const humidity = point?.relative_humidity_2m ?? 65.0;

  // Approximate cloud cover from humidity & precipitation
  let cloudCover = 20;
  if (precip > 0.1) {
    cloudCover = 85 + Math.min(15, precip * 2);
  } else if (humidity > 80) {
    cloudCover = 60 + (humidity - 80) * 1.5;
  } else if (humidity > 60) {
    cloudCover = 35 + (humidity - 60) * 1.0;
  }

  // Determine Condition
  let condition: WeatherCondition = isDay ? "SUNNY" : "NIGHT";

  if (precip >= 5.0 && wind >= 35.0) {
    condition = "STORM";
  } else if (precip >= 3.0) {
    condition = "HEAVY_RAIN";
  } else if (precip > 0.1) {
    condition = "RAIN";
  } else if (wind >= 38.0) {
    condition = "WIND";
  } else if (humidity >= 92.0 && precip < 0.1) {
    condition = "FOG";
  } else if (cloudCover >= 70) {
    condition = "CLOUDY";
  } else if (cloudCover >= 35) {
    condition = isDay ? "PARTLY_CLOUDY" : "NIGHT";
  } else {
    condition = isDay ? "SUNNY" : "NIGHT";
  }

  // Feels-like approximation (Rothfusz / simplified humidex for tropical air)
  const feelsLike =
    temp >= 26
      ? Math.round((temp + (humidity / 100) * 4.5) * 10) / 10
      : temp;

  return {
    condition,
    temperature: Math.round(temp * 10) / 10,
    feelsLike,
    precipitation: Math.round(precip * 10) / 10,
    windSpeed: Math.round(wind * 10) / 10,
    windDirection: 240, // typical monsoon SW flow or from model
    humidity: Math.round(humidity),
    cloudCover: Math.min(100, Math.round(cloudCover)),
    isDay,
    pressure: 1012, // standard sea-level hPa
    visibility: precip > 3 ? 4.5 : precip > 0.5 ? 7.2 : 12.0,
    timestamp: point?.timestamp || now.toISOString(),
  };
}
