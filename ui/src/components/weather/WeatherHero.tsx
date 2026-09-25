"use client";

import { useMemo } from "react";
import { 
  MapPin, 
  Wind, 
  Droplets, 
  Compass, 
  CloudRain, 
  Sun, 
  Cloud, 
  CloudLightning, 
  Eye, 
  Clock, 
  Sparkles
} from "lucide-react";
import { NormalizedWeatherState, WeatherCondition } from "@/types/weather";
import { WeatherScene } from "@/components/weather-scene/WeatherScene";
import { LocationItem } from "@/context/LocationContext";
import { useSettings } from "@/context/SettingsContext";

interface WeatherHeroProps {
  weather: NormalizedWeatherState;
  location: LocationItem;
  ensembleValue?: number | null;
  modelSpread?: number | null;
  lastRefreshed?: Date | null;
  validTime?: string;
}

function getConditionIcon(condition: WeatherCondition) {
  switch (condition) {
    case "SUNNY":
      return <Sun className="w-5 h-5 text-amber-400 animate-spin-slow" />;
    case "PARTLY_CLOUDY":
    case "CLOUDY":
      return <Cloud className="w-5 h-5 text-slate-300" />;
    case "RAIN":
    case "HEAVY_RAIN":
      return <CloudRain className="w-5 h-5 text-sky-400" />;
    case "STORM":
      return <CloudLightning className="w-5 h-5 text-indigo-400" />;
    case "WIND":
      return <Wind className="w-5 h-5 text-cyan-400" />;
    default:
      return <Sun className="w-5 h-5 text-amber-400" />;
  }
}

export function WeatherHero({
  weather,
  location,
  ensembleValue,
  modelSpread,
  lastRefreshed,
  validTime,
}: WeatherHeroProps) {
  const { convertTemp, convertTempDelta, convertWind, tempSymbol, windSymbol } = useSettings();

  const formattedCondition = useMemo(() => {
    return weather.condition.replace("_", " ");
  }, [weather.condition]);

  const rawTemp = ensembleValue !== null && ensembleValue !== undefined ? Number(ensembleValue) : weather.temperature;
  const displayTemp = convertTemp(rawTemp);
  const displayWind = convertWind(weather.windSpeed);
  const displaySpread = modelSpread !== null && modelSpread !== undefined ? convertTempDelta(Number(modelSpread)) : null;

  return (
    <div className="relative rounded-2xl overflow-hidden border border-border-subtle/80 shadow-2xl min-h-[300px] flex flex-col justify-between p-5 sm:p-7 text-white">
      {/* 3D Atmospheric WeatherScene Background */}
      <WeatherScene weather={weather} />

      {/* Top Bar: Station Identity & Data Freshness */}
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-background/60 backdrop-blur-md border border-white/10 flex items-center justify-center text-ensemble shadow-inner">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg sm:text-xl font-extrabold tracking-tight text-white font-sans">
                {location.name}
              </h2>
              <span className="text-[11px] font-mono text-text-muted bg-background/50 px-2 py-0.5 rounded border border-white/5">
                {location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E
              </span>
            </div>
            <span className="text-xs text-text-secondary font-sans">
              {location.region || "Operational Station"}
            </span>
          </div>
        </div>

        {/* Live Freshness & Ensemble Status */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-ensemble/15 border border-ensemble/30 text-ensemble text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span className="font-semibold">ADAPTIVE ENSEMBLE ACTIVE</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-background/60 border border-white/10 text-text-muted text-[11px] font-mono">
            <Clock className="w-3 h-3" />
            <span>{lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "LIVE"}</span>
          </div>
        </div>
      </div>

      {/* Main Meteorological Display: Hero Metric */}
      <div className="relative z-10 my-4 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-secondary bg-background/40 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 w-fit">
            {getConditionIcon(weather.condition)}
            <span className="font-bold text-white">{formattedCondition}</span>
          </div>

          <div>
            <div className="text-sm font-semibold text-ensemble tracking-wider uppercase mb-1">
              Ensemble Forecast
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-6xl sm:text-7xl lg:text-8xl font-black tracking-tighter text-white font-sans drop-shadow-md">
                {displayTemp.toFixed(1)}°
              </span>
              <span className="text-2xl font-bold text-text-secondary">{tempSymbol.replace("°", "")}</span>
            </div>
          </div>
          
          <div className="text-xs text-text-muted font-mono flex items-center gap-1.5 mt-2">
            <Clock className="w-3.5 h-3.5" />
            <span>Forecast valid: {validTime ? new Date(validTime).toLocaleString() : "Unknown"}</span>
          </div>
        </div>

        {/* Right Metric Quick-Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 bg-background/40 backdrop-blur-md p-3 rounded-xl border border-white/10 shadow-lg">
          {/* Wind */}
          <div className="p-2 sm:p-2.5 rounded-lg bg-panel/40 border border-white/5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted font-mono">
              <Wind className="w-3.5 h-3.5 text-cyan-400" />
              <span>WIND</span>
            </div>
            <div className="text-sm sm:text-base font-bold text-white font-sans">
              {displayWind.toFixed(1)} <span className="text-[11px] font-normal text-text-secondary">{windSymbol}</span>
            </div>
          </div>

          {/* Humidity */}
          <div className="p-2 sm:p-2.5 rounded-lg bg-panel/40 border border-white/5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted font-mono">
              <Droplets className="w-3.5 h-3.5 text-blue-400" />
              <span>HUMIDITY</span>
            </div>
            <div className="text-sm sm:text-base font-bold text-white font-sans">
              {weather.humidity}<span className="text-[11px] font-normal text-text-secondary">%</span>
            </div>
          </div>

          {/* Precipitation */}
          <div className="p-2 sm:p-2.5 rounded-lg bg-panel/40 border border-white/5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted font-mono">
              <CloudRain className="w-3.5 h-3.5 text-sky-400" />
              <span>PRECIP</span>
            </div>
            <div className="text-sm sm:text-base font-bold text-white font-sans">
              {weather.precipitation} <span className="text-[11px] font-normal text-text-secondary">mm</span>
            </div>
          </div>

          {/* Model Spread */}
          <div className="p-2 sm:p-2.5 rounded-lg bg-panel/40 border border-white/5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted font-mono">
              <Compass className="w-3.5 h-3.5 text-amber-400" />
              <span>SPREAD</span>
            </div>
            <div className="text-sm sm:text-base font-bold text-amber-400 font-sans">
              {displaySpread !== null ? `±${displaySpread.toFixed(1)}°` : "±0.5°"}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Sub-bar: Scientific Transparency Disclaimer */}
      <div className="relative z-10 pt-3 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] text-text-muted font-mono">
        <div className="flex items-center gap-1.5">
          <Eye className="w-3 h-3 text-ensemble" />
          <span>Operational NWP multi-model forecast field — not station observation</span>
        </div>
        <span>ERA5 = Reanalysis Benchmark</span>
      </div>
    </div>
  );
}
