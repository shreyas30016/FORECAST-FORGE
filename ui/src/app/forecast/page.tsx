"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { format, parseISO } from "date-fns";
import { api } from "@/lib/api";
import { ForecastResponse, TimelineRow } from "@/types/api";
import { ForecastTimeline } from "@/components/charts/ForecastTimeline";
import { useLocation } from "@/context/LocationContext";
import { useSettings } from "@/context/SettingsContext";
import { useCopilot } from "@/context/CopilotContext";
import { 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  Thermometer, 
  Droplets, 
  CloudRain, 
  Wind,
  Sparkles,
  GitCompare,
  TrendingUp,
  MapPin
} from "lucide-react";

const VARIABLES = [
  { id: "temperature_2m", name: "2m Temperature", unit: "°C", icon: Thermometer, color: "text-amber-400" },
  { id: "relative_humidity_2m", name: "Relative Humidity", unit: "%", icon: Droplets, color: "text-blue-400" },
  { id: "precipitation", name: "Precipitation", unit: " mm", icon: CloudRain, color: "text-sky-400" },
  { id: "wind_speed_10m", name: "10m Wind Speed", unit: " km/h", icon: Wind, color: "text-cyan-400" },
];

const HORIZONS = [
  { hours: 24, label: "24h Evolution" },
  { hours: 48, label: "48h Timeline" },
  { hours: 72, label: "72h Complete" },
];

export default function ForecastPage() {
  const { location } = useLocation();
  const { setCopilotContext } = useCopilot();
  const { convertTemp, convertWind, tempSymbol, windSymbol } = useSettings();
  const [horizon, setHorizon] = useState<number>(72);
  const [variable, setVariable] = useState<string>("temperature_2m");
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCopilotContext({
      page: "forecast",
      location: location.name,
      latitude: location.latitude,
      longitude: location.longitude,
      variable: variable,
      lead_time_hours: horizon,
    });
  }, [location.name, location.latitude, location.longitude, variable, horizon, setCopilotContext]);

  const activeVar = useMemo(() => {
    const base = VARIABLES.find((v) => v.id === variable) || VARIABLES[0];
    let dynUnit = base.unit;
    if (base.id === "temperature_2m") dynUnit = tempSymbol;
    else if (base.id === "wind_speed_10m") dynUnit = ` ${windSymbol}`;
    return { ...base, unit: dynUnit };
  }, [variable, tempSymbol, windSymbol]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getForecast(location.latitude, location.longitude, horizon, location.name);
      setForecast(res);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load forecast data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [location.latitude, location.longitude, location.name, horizon]);

  useEffect(() => {
    let ignore = false;
    async function run() {
      try {
        const res = await api.getForecast(location.latitude, location.longitude, horizon, location.name);
        if (!ignore) {
          setForecast(res);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load forecast data";
          setError(msg);
          setLoading(false);
        }
      }
    }
    run();
    return () => {
      ignore = true;
    };
  }, [location.latitude, location.longitude, location.name, horizon]);

  // Transform records for timeline and table
  const { timelineData, tableRows, summaryStats } = useMemo(() => {
    if (!forecast) return { timelineData: [], tableRows: [], summaryStats: null };

    const timeMap: Record<string, TimelineRow> = {};

    for (const [model, pData] of Object.entries(forecast.providers)) {
      if (!pData?.records) continue;
      pData.records.forEach((r) => {
        if (!timeMap[r.timestamp]) {
          timeMap[r.timestamp] = { timestamp: r.timestamp };
        }
        const val = r[variable as keyof typeof r] as number | null;
        timeMap[r.timestamp][model] = val;
      });
    }

    const isTemp = variable === "temperature_2m";
    const isWind = variable === "wind_speed_10m";

    const convertVal = (v: unknown): number | null => {
      if (v === null || v === undefined || typeof v !== "number" || isNaN(v)) return null;
      if (isTemp) return parseFloat(convertTemp(v).toFixed(2));
      if (isWind) return parseFloat(convertWind(v).toFixed(2));
      return v;
    };

    const allValues: number[] = [];

    const sorted = Object.values(timeMap)
      .map((row) => {
        const rawIfs = row.ecmwf_ifs025 as number | null;
        const rawGfs = row.gfs_seamless as number | null;
        const rawAifs = row.ecmwf_aifs025 as number | null;

        const ifs = convertVal(rawIfs);
        const gfs = convertVal(rawGfs);
        const aifs = convertVal(rawAifs);

        const vals = [ifs, gfs].filter((v): v is number => v !== null && v !== undefined);
        const ens = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
        const spread = vals.length === 2 ? Math.abs(ifs! - gfs!) : null;

        if (ens !== null) allValues.push(ens);

        return {
          ...row,
          ecmwf_ifs025: ifs,
          gfs_seamless: gfs,
          ecmwf_aifs025: aifs,
          ensemble: ens !== null ? parseFloat(ens.toFixed(2)) : null,
          spread: spread !== null ? parseFloat(spread.toFixed(2)) : null,
        };
      })
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    const min = allValues.length ? Math.min(...allValues).toFixed(1) : "—";
    const max = allValues.length ? Math.max(...allValues).toFixed(1) : "—";
    const avg = allValues.length ? (allValues.reduce((a, b) => a + b, 0) / allValues.length).toFixed(1) : "—";

    return { 
      timelineData: sorted, 
      tableRows: sorted,
      summaryStats: { min, max, avg }
    };
  }, [forecast, variable, convertTemp, convertWind]);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans">
      
      {/* 1. Header & Operational Control Bar */}
      <div className="p-5 sm:p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-ensemble animate-pulse" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-ensemble font-semibold">
              Multi-Model Forecast Horizon
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Forecast Trajectory &amp; Consensus
          </h1>
          <div className="flex items-center gap-2 text-xs font-mono text-text-muted mt-1">
            <MapPin className="w-3.5 h-3.5 text-ensemble" />
            <span>Target: {location.name} [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]</span>
          </div>
        </div>

        {/* Quick Horizon & Refresh */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Horizon Pills */}
          <div className="flex items-center bg-background/80 p-1 rounded-xl border border-border-subtle">
            <Clock className="w-3.5 h-3.5 text-text-muted ml-2 mr-1" />
            <div className="flex items-center gap-1">
              {HORIZONS.map((h) => (
                <button
                  key={h.hours}
                  type="button"
                  onClick={() => setHorizon(h.hours)}
                  className={`px-3 py-1 rounded-lg text-xs font-mono transition-all duration-200 ${
                    horizon === h.hours
                      ? "bg-ensemble text-slate-950 font-bold shadow-md"
                      : "text-text-secondary hover:text-white"
                  }`}
                >
                  {h.hours}h
                </button>
              ))}
            </div>
          </div>

          {/* Sync Button */}
          <button
            type="button"
            onClick={fetchData}
            className="p-2 bg-background/80 hover:bg-panel-hover border border-border-subtle hover:border-ensemble/40 text-text-secondary hover:text-white rounded-xl transition-all shadow-sm"
            title="Refresh forecast data"
            aria-label="Refresh forecast"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-ensemble" : ""}`} />
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-status-unavailable/15 border border-status-unavailable/40 rounded-xl text-white text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-status-unavailable shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchData}
            className="px-3 py-1 rounded bg-status-unavailable/30 hover:bg-status-unavailable/50 font-bold"
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. Variable Selector Tabs & Horizon Summary Strip */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Variable Selector Pills */}
        <div className="lg:col-span-8 flex flex-wrap items-center gap-2">
          {VARIABLES.map((v) => {
            const isActive = variable === v.id;
            const Icon = v.icon;
            return (
              <button
                key={v.id}
                type="button"
                onClick={() => setVariable(v.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 border ${
                  isActive
                    ? "bg-panel-elevated text-white border-ensemble/50 shadow-md ring-1 ring-ensemble/30"
                    : "bg-panel/60 text-text-secondary border-border-subtle hover:text-white hover:bg-panel"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${v.color}`} />
                <span>{v.name}</span>
                <span className="text-[10px] font-mono text-text-muted">({v.unit.trim()})</span>
              </button>
            );
          })}
        </div>

        {/* Min / Mean / Max Horizon Summary Stat Pill */}
        {summaryStats && (
          <div className="lg:col-span-4 flex items-center justify-end gap-3 font-mono text-xs text-text-secondary bg-panel/50 px-3.5 py-2 rounded-xl border border-white/5">
            <TrendingUp className="w-3.5 h-3.5 text-ensemble" />
            <span>Min: <strong className="text-white">{summaryStats.min}</strong></span>
            <span>•</span>
            <span>Avg: <strong className="text-white">{summaryStats.avg}</strong></span>
            <span>•</span>
            <span>Max: <strong className="text-white">{summaryStats.max}{activeVar.unit}</strong></span>
          </div>
        )}
      </div>

      {/* 3. Main Trajectory Chart Canvas */}
      <div className="p-5 sm:p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-ensemble" />
            <h2 className="text-base font-extrabold text-white tracking-tight">
              {activeVar.name} Consensus Curve
            </h2>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            {tableRows.length}h lead • 0.25° grid resolution
          </span>
        </div>

        {loading ? (
          <div className="h-72 flex flex-col items-center justify-center text-xs font-mono text-text-muted gap-2 animate-pulse">
            <RefreshCw className="w-5 h-5 text-ensemble animate-spin" />
            <span>Synthesizing multi-model forecast trajectory...</span>
          </div>
        ) : (
          <ForecastTimeline data={timelineData} variable={variable} unit={activeVar.unit} />
        )}
      </div>

      {/* 4. Cross-Model Hourly Prediction & Spread Table */}
      <div className="rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-border-subtle flex items-center justify-between bg-background/40">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-ensemble" />
            <h2 className="text-base font-extrabold text-white tracking-tight">
              Hourly Predictions &amp; Model Spread
            </h2>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            Live model outputs
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border-subtle bg-background/60 text-text-muted text-[11px] font-mono">
                <th className="py-2.5 px-4 font-semibold">Valid Time (UTC)</th>
                <th className="py-2.5 px-4 font-semibold text-ifs">ECMWF IFS</th>
                <th className="py-2.5 px-4 font-semibold text-gfs">NOAA GFS</th>
                <th className="py-2.5 px-4 font-semibold text-aifs">ECMWF AIFS · AI Model</th>
                <th className="py-2.5 px-4 font-semibold text-ensemble">Ensemble</th>
                <th className="py-2.5 px-4 font-semibold text-amber-400">Spread (|IFS − GFS|)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/40 font-mono text-xs">
              {tableRows.slice(0, 36).map((row) => {
                const dateObj = parseISO(row.timestamp);
                const ifs = row.ecmwf_ifs025 as number | null;
                const gfs = row.gfs_seamless as number | null;
                const aifs = row.ecmwf_aifs025 as number | null;
                const delta = ifs !== null && gfs !== null ? Math.abs(ifs - gfs).toFixed(2) : "—";

                return (
                  <tr key={row.timestamp} className="hover:bg-panel-hover/40 transition-colors">
                    <td className="py-2 px-4 text-text-secondary whitespace-nowrap">
                      {format(dateObj, "yyyy-MM-dd HH:mm")} UTC
                    </td>
                    <td className="py-2 px-4 text-white font-medium">
                      {ifs !== null ? `${ifs.toFixed(1)}${activeVar.unit}` : "—"}
                    </td>
                    <td className="py-2 px-4 text-white font-medium">
                      {gfs !== null ? `${gfs.toFixed(1)}${activeVar.unit}` : "—"}
                    </td>
                    <td className="py-2 px-4 text-text-muted font-medium">
                      {aifs !== null ? `${aifs.toFixed(1)}${activeVar.unit}` : "— (Excluded)"}
                    </td>
                    <td className="py-2 px-4 text-ensemble font-bold">
                      {row.ensemble !== null ? `${(row.ensemble as number).toFixed(1)}${activeVar.unit}` : "—"}
                    </td>
                    <td className="py-2 px-4 text-amber-400">
                      {delta !== "—" ? (
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${Number(delta) > 2.5 ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "text-text-secondary"}`}>
                          ±{delta}{activeVar.unit}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {tableRows.length > 36 && (
            <div className="p-2.5 text-center text-[11px] font-mono text-text-muted border-t border-border-subtle bg-background/40">
              Showing initial 36 of {tableRows.length} hourly steps
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
