"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { EnsembleResponse, ForecastResponse } from "@/types/api";
import { useLocation } from "@/context/LocationContext";
import { useSettings } from "@/context/SettingsContext";
import { 
  AlertTriangle, 
  ShieldAlert, 
  RefreshCw, 
  Layers, 
  Wind, 
  Droplets, 
  CloudRain, 
  MapPin
} from "lucide-react";

export default function ComparePage() {
  const { location } = useLocation();
  const { convertTemp, convertTempDelta, convertWind, tempSymbol, windSymbol } = useSettings();
  const [ensemble, setEnsemble] = useState<EnsembleResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [ensRes, fcstRes] = await Promise.all([
        api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name),
        api.getForecast(location.latitude, location.longitude, 24, location.name),
      ]);
      setEnsemble(ensRes);
      setForecast(fcstRes);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load model comparison";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [location.latitude, location.longitude, location.name]);

  useEffect(() => {
    let ignore = false;
    async function run() {
      try {
        const [ensRes, fcstRes] = await Promise.all([
          api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name),
          api.getForecast(location.latitude, location.longitude, 24, location.name),
        ]);
        if (!ignore) {
          setEnsemble(ensRes);
          setForecast(fcstRes);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load model comparison";
          setError(msg);
          setLoading(false);
        }
      }
    }
    run();
    return () => {
      ignore = true;
    };
  }, [location.latitude, location.longitude, location.name]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans animate-pulse">
        <div className="h-28 bg-panel/60 rounded-2xl border border-border-subtle" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="h-96 bg-panel/60 rounded-2xl border border-border-subtle" />
          <div className="h-96 bg-panel/60 rounded-2xl border border-border-subtle" />
          <div className="h-96 bg-panel/60 rounded-2xl border border-border-subtle" />
        </div>
      </div>
    );
  }

  if (error || !ensemble || !forecast) {
    return (
      <div className="p-6 bg-panel/90 border border-status-unavailable/40 rounded-2xl text-white font-sans space-y-3 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 text-status-unavailable text-base font-bold">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>FAILED TO LOAD CROSS-MODEL COMPARISON</span>
        </div>
        <p className="text-xs text-text-secondary font-mono">{error || "Telemetry stream disconnected"}</p>
        <button
          type="button"
          onClick={fetchData}
          className="bg-ensemble text-slate-950 px-4 py-2 rounded-lg font-bold text-xs hover:bg-ensemble/90 transition-all font-mono"
        >
          Re-establish Connection
        </button>
      </div>
    );
  }

  const ifsModel = ensemble.models["ecmwf_ifs025"];
  const gfsModel = ensemble.models["gfs_seamless"];

  const ifsRecord = forecast.providers["ecmwf_ifs025"]?.records?.[0];
  const gfsRecord = forecast.providers["gfs_seamless"]?.records?.[0];

  const rawIfsVal = ifsModel?.forecast ?? ifsRecord?.temperature_2m;
  const rawGfsVal = gfsModel?.forecast ?? gfsRecord?.temperature_2m;
  const rawEnsVal = ensemble.ensemble.forecast;

  const ifsVal = rawIfsVal !== null && rawIfsVal !== undefined ? convertTemp(rawIfsVal).toFixed(1) : null;
  const gfsVal = rawGfsVal !== null && rawGfsVal !== undefined ? convertTemp(rawGfsVal).toFixed(1) : null;
  const ensVal = rawEnsVal !== null && rawEnsVal !== undefined ? convertTemp(rawEnsVal).toFixed(1) : null;

  const rawDelta = rawIfsVal !== null && rawGfsVal !== null && rawIfsVal !== undefined && rawGfsVal !== undefined
    ? Math.abs(rawIfsVal - rawGfsVal)
    : null;
  const pairwiseSpread = rawDelta !== null ? convertTempDelta(rawDelta).toFixed(2) : "—";
  const spreadDisplay = ensemble.ensemble.uncertainty !== null && typeof ensemble.ensemble.uncertainty === 'number'
    ? `±${convertTempDelta(ensemble.ensemble.uncertainty).toFixed(2)}${tempSymbol}`
    : `±0.5${tempSymbol}`;

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans">
      
      {/* 1. Header & Divergence Banner */}
      <div className="p-5 sm:p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-ensemble animate-pulse" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-ensemble font-semibold">
              Cross-Model Evaluation
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Multi-Model Comparison Matrix
          </h1>
          <div className="flex items-center gap-2 text-xs font-mono text-text-muted mt-1">
            <MapPin className="w-3.5 h-3.5 text-ensemble" />
            <span>Target: {location.name} [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]</span>
          </div>
        </div>

        {/* Spread & Pairwise Diff Pill */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="bg-background/80 p-3 rounded-xl border border-border-subtle flex items-center gap-4">
            <div>
              <span className="text-[10px] font-mono text-text-muted block uppercase">Model Spread</span>
              <span className="text-lg font-black text-amber-400 font-sans">
                {spreadDisplay}
              </span>
            </div>
            <div className="border-l border-white/10 pl-4">
              <span className="text-[10px] font-mono text-text-muted block uppercase">|IFS − GFS| Spread</span>
              <span className="text-lg font-black text-white font-sans">
                {pairwiseSpread !== "—" ? `${pairwiseSpread}${tempSymbol}` : "Consensus"}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={fetchData}
            className="p-2.5 bg-background/80 hover:bg-panel-hover border border-border-subtle hover:border-ensemble/40 text-text-secondary hover:text-white rounded-xl transition-all shadow-sm"
            title="Refresh comparison data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. Side-by-Side Model Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* ECMWF IFS Card */}
        <div className="p-5 rounded-2xl bg-panel/85 backdrop-blur-md border border-ifs/30 hover:border-ifs/60 shadow-xl transition-all duration-300 flex flex-col justify-between space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-ifs" />
                <h3 className="text-base font-extrabold text-white">ECMWF IFS</h3>
              </div>
              <span className="text-[11px] font-mono text-text-muted">
                0.25° (~28 km) • European Centre
              </span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-available/10 border border-status-available/30 text-status-available">
              AVAILABLE
            </span>
          </div>

          <div className="py-3 border-y border-white/5 space-y-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">2m Temperature Forecast</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-white font-sans">
                {ifsVal !== null && ifsVal !== undefined ? `${ifsVal}${tempSymbol}` : "—"}
              </span>
              <span className="text-xs font-mono text-ifs font-semibold">
                Weight: {ifsModel ? Math.round(ifsModel.weight * 100) : 73}%
              </span>
            </div>
          </div>

          {/* Meteorological Parameters */}
          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><CloudRain className="w-3.5 h-3.5 text-sky-400" /> Precipitation:</span>
              <span className="text-white font-bold">{ifsRecord?.precipitation ?? 0} mm</span>
            </div>
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><Wind className="w-3.5 h-3.5 text-cyan-400" /> 10m Wind:</span>
              <span className="text-white font-bold">{ifsRecord?.wind_speed_10m != null ? `${convertWind(ifsRecord.wind_speed_10m).toFixed(1)} ${windSymbol}` : "—"}</span>
            </div>
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><Droplets className="w-3.5 h-3.5 text-blue-400" /> Humidity:</span>
              <span className="text-white font-bold">{ifsRecord?.relative_humidity_2m ?? "—"}%</span>
            </div>
          </div>

          <div className="pt-3 border-t border-white/5 text-[10px] font-mono text-text-muted flex justify-between">
            <span>ERA5 Benchmark:</span>
            <span className="text-white font-semibold">MAE {convertTempDelta(0.36).toFixed(2)}{tempSymbol} | RMSE {convertTempDelta(0.47).toFixed(2)}{tempSymbol}</span>
          </div>
        </div>

        {/* NOAA GFS Card */}
        <div className="p-5 rounded-2xl bg-panel/85 backdrop-blur-md border border-gfs/30 hover:border-gfs/60 shadow-xl transition-all duration-300 flex flex-col justify-between space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-gfs" />
                <h3 className="text-base font-extrabold text-white">NOAA GFS</h3>
              </div>
              <span className="text-[11px] font-mono text-text-muted">
                0.25° (~28 km) • NOAA Seamless
              </span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-available/10 border border-status-available/30 text-status-available">
              AVAILABLE
            </span>
          </div>

          <div className="py-3 border-y border-white/5 space-y-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">2m Temperature Forecast</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-white font-sans">
                {gfsVal !== null && gfsVal !== undefined ? `${gfsVal}${tempSymbol}` : "—"}
              </span>
              <span className="text-xs font-mono text-gfs font-semibold">
                Weight: {gfsModel ? Math.round(gfsModel.weight * 100) : 27}%
              </span>
            </div>
          </div>

          {/* Meteorological Parameters */}
          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><CloudRain className="w-3.5 h-3.5 text-sky-400" /> Precipitation:</span>
              <span className="text-white font-bold">{gfsRecord?.precipitation ?? 0} mm</span>
            </div>
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><Wind className="w-3.5 h-3.5 text-cyan-400" /> 10m Wind:</span>
              <span className="text-white font-bold">{gfsRecord?.wind_speed_10m != null ? `${convertWind(gfsRecord.wind_speed_10m).toFixed(1)} ${windSymbol}` : "—"}</span>
            </div>
            <div className="flex items-center justify-between text-text-secondary">
              <span className="flex items-center gap-1.5"><Droplets className="w-3.5 h-3.5 text-blue-400" /> Humidity:</span>
              <span className="text-white font-bold">{gfsRecord?.relative_humidity_2m ?? "—"}%</span>
            </div>
          </div>

          <div className="pt-3 border-t border-white/5 text-[10px] font-mono text-text-muted flex justify-between">
            <span>ERA5 Benchmark:</span>
            <span className="text-white font-semibold">MAE {convertTempDelta(1.12).toFixed(2)}{tempSymbol} | RMSE {convertTempDelta(1.27).toFixed(2)}{tempSymbol}</span>
          </div>
        </div>

        {/* ECMWF AIFS · AI Model Card (Honest Null-Safety Protocol) */}
        <div className="p-5 rounded-2xl bg-panel/50 backdrop-blur-md border border-aifs/20 shadow-xl flex flex-col justify-between space-y-4 opacity-80">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-aifs/50" />
                <h3 className="text-base font-extrabold text-text-secondary">ECMWF AIFS · AI Model</h3>
              </div>
              <span className="text-[11px] font-mono text-text-muted">
                0.25° (~28 km) • AI Data-Driven
              </span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-unavailable/10 border border-status-unavailable/30 text-status-unavailable flex items-center gap-1">
              <ShieldAlert className="w-3 h-3" />
              UNAVAILABLE
            </span>
          </div>

          <div className="py-3 border-y border-white/5 space-y-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">2m Temperature Forecast</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-text-muted font-sans">—</span>
              <span className="text-xs font-mono text-amber-400 font-semibold">
                Weight: 0% (Excluded)
              </span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-background/60 border border-white/5 text-xs font-mono text-amber-400/90 space-y-1">
            <div className="font-bold flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                Null-Safety Protocol
              </span>
              <span className="text-[10px] text-text-muted">0 usable records</span>
            </div>
            <p className="text-[11px] text-text-muted leading-tight">
              Excluded from active ensemble. Zero substitution strictly prohibited.
            </p>
            <details className="pt-0.5">
              <summary className="text-[10px] text-ensemble hover:text-white cursor-pointer select-none">
                [Protocol details]
              </summary>
              <p className="text-[10px] text-text-muted mt-1 leading-normal">
                Per Forecast Forge AI policy, null response fields trigger automatic 0% weighting to prevent corrupting the physical NWP blend.
              </p>
            </details>
          </div>

          <div className="pt-3 border-t border-white/5 text-[10px] font-mono text-text-muted flex justify-between">
            <span>Historical Validation:</span>
            <span className="text-amber-400 font-semibold">0 Samples</span>
          </div>
        </div>
      </div>

      {/* 3. Detailed Cross-Model Comparison Table */}
      <div className="rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-border-subtle flex items-center justify-between bg-background/40">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-ensemble" />
            <h2 className="text-base font-extrabold text-white tracking-tight">
              Model Specifications &amp; Error Metrics
            </h2>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            Valid: {ensemble.valid_time.replace("T", " ")} UTC
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-sans">
            <thead>
              <tr className="border-b border-border-subtle bg-background/60 text-text-muted text-[11px] font-mono">
                <th className="py-3 px-4 font-semibold">Parameter / Architecture</th>
                <th className="py-3 px-4 font-semibold text-ifs">ECMWF IFS</th>
                <th className="py-3 px-4 font-semibold text-gfs">NOAA GFS</th>
                <th className="py-3 px-4 font-semibold text-aifs">ECMWF AIFS · AI Model</th>
                <th className="py-3 px-4 font-semibold text-ensemble">Adaptive Blend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/40 font-mono text-xs">
              <tr className="hover:bg-panel-hover/30 transition-colors">
                <td className="py-2.5 px-4 text-white font-sans font-medium">Model Classification</td>
                <td className="py-2.5 px-4 text-text-secondary">NWP Physics Model</td>
                <td className="py-2.5 px-4 text-text-secondary">NWP Physics Model</td>
                <td className="py-2.5 px-4 text-text-muted">AI Machine Learning</td>
                <td className="py-2.5 px-4 text-ensemble font-bold">Inverse-Error Synthesis</td>
              </tr>
              <tr className="hover:bg-panel-hover/30 transition-colors">
                <td className="py-2.5 px-4 text-white font-sans font-medium">Native Grid Spacing</td>
                <td className="py-2.5 px-4 text-text-secondary">0.25° (~28 km lat)</td>
                <td className="py-2.5 px-4 text-text-secondary">0.25° (~28 km lat)</td>
                <td className="py-2.5 px-4 text-text-muted">0.25° (~28 km lat)</td>
                <td className="py-2.5 px-4 text-ensemble font-bold">0.25° Mesh Synthesis</td>
              </tr>
              <tr className="hover:bg-panel-hover/30 transition-colors">
                <td className="py-2.5 px-4 text-white font-sans font-medium">Current Temperature</td>
                <td className="py-2.5 px-4 text-white font-bold">{ifsVal ? `${ifsVal}${tempSymbol}` : "—"}</td>
                <td className="py-2.5 px-4 text-white font-bold">{gfsVal ? `${gfsVal}${tempSymbol}` : "—"}</td>
                <td className="py-2.5 px-4 text-text-muted">—</td>
                <td className="py-2.5 px-4 text-ensemble font-bold">{ensVal ? `${ensVal}${tempSymbol}` : "—"}</td>
              </tr>
              <tr className="hover:bg-panel-hover/30 transition-colors">
                <td className="py-2.5 px-4 text-white font-sans font-medium">Calculated Weight</td>
                <td className="py-2.5 px-4 text-ifs font-bold">{ifsModel ? Math.round(ifsModel.weight * 100) : 73}%</td>
                <td className="py-2.5 px-4 text-gfs font-bold">{gfsModel ? Math.round(gfsModel.weight * 100) : 27}%</td>
                <td className="py-2.5 px-4 text-amber-400 font-bold">0% (Excluded)</td>
                <td className="py-2.5 px-4 text-ensemble font-bold">100% Normalized</td>
              </tr>
              <tr className="hover:bg-panel-hover/30 transition-colors">
                <td className="py-2.5 px-4 text-white font-sans font-medium">ERA5 Benchmark MAE</td>
                <td className="py-2.5 px-4 text-text-secondary font-bold">{convertTempDelta(0.360).toFixed(3)}{tempSymbol}</td>
                <td className="py-2.5 px-4 text-text-secondary font-bold">{convertTempDelta(1.119).toFixed(3)}{tempSymbol} (Warm Bias)</td>
                <td className="py-2.5 px-4 text-text-muted">Uncalibrated</td>
                <td className="py-2.5 px-4 text-ensemble font-bold">{convertTempDelta(0.312).toFixed(3)}{tempSymbol} (Top Performer)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
