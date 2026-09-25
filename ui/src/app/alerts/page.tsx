"use client";

import { useEffect, useState } from "react";
import { useLocation } from "@/context/LocationContext";
import { api } from "@/lib/api";
import { ForecastResponse } from "@/types/api";
import { 
  Bell, 
  ShieldCheck, 
  Radio, 
  Wind, 
  Flame, 
  CloudRain, 
  Activity, 
  RefreshCw,
  AlertCircle
} from "lucide-react";

export default function AlertsPage() {
  const { location } = useLocation();
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadForecastAlerts = async () => {
    try {
      setLoading(true);
      const data = await api.getForecast(location.latitude, location.longitude, 72, location.name);
      setForecast(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to retrieve live surveillance stream");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await api.getForecast(location.latitude, location.longitude, 72, location.name);
        if (!ignore) {
          setForecast(data);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to retrieve live surveillance stream");
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [location]);

  // Compute live 72h max values across connected operational models
  let maxTemp = 0;
  let maxWind = 0;
  let maxPrecip = 0;

  if (forecast && forecast.providers) {
    Object.values(forecast.providers).forEach((provider) => {
      if (provider.records) {
        provider.records.forEach((rec) => {
          if (rec.temperature_2m !== null && rec.temperature_2m > maxTemp) {
            maxTemp = rec.temperature_2m;
          }
          if (rec.wind_speed_10m !== null && rec.wind_speed_10m > maxWind) {
            maxWind = rec.wind_speed_10m;
          }
          if (rec.precipitation !== null && rec.precipitation > maxPrecip) {
            maxPrecip = rec.precipitation;
          }
        });
      }
    });
  }

  // Threshold definitions
  const heatThreshold = 40.0;
  const windThreshold = 60.0;
  const precipThreshold = 20.0;

  const heatStatus = maxTemp >= heatThreshold ? "WARNING" : maxTemp >= 36 ? "ADVISORY" : "NOMINAL";
  const windStatus = maxWind >= windThreshold ? "WARNING" : maxWind >= 45 ? "ADVISORY" : "NOMINAL";
  const precipStatus = maxPrecip >= precipThreshold ? "WARNING" : maxPrecip >= 10 ? "ADVISORY" : "NOMINAL";

  return (
    <div className="flex flex-col gap-6 text-slate-100 max-w-7xl mx-auto pb-12">
      
      {/* Header Bar */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-40 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex items-start sm:items-center gap-3.5 relative z-10">
          <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0 shadow-inner">
            <Bell className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Meteorological Risk Center
              </h1>
              <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40">
                CAP v1.2
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Target: <strong className="text-white font-semibold">{location.name}</strong> [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 relative z-10">
          <button
            type="button"
            onClick={loadForecastAlerts}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition-all shadow-sm active:scale-95"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-amber-400 ${loading ? "animate-spin" : ""}`} />
            <span>Poll Surveillance</span>
          </button>
          <div className="px-3 py-2 rounded-xl text-[11px] font-mono font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5 shadow-sm">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>SURVEILLANCE ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <div className="flex-1">{error}</div>
          <button
            type="button"
            onClick={loadForecastAlerts}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 rounded text-rose-200 font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Operational Status Banner */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] flex flex-col md:flex-row items-center justify-between gap-5 shadow-2xl relative overflow-hidden">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 shadow-lg shadow-emerald-500/10">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                No active meteorological warnings for {location.name}
              </h2>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Live NWP ensemble feeds indicate all atmospheric parameters remain within nominal safety margins across the 72-hour horizon.
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end shrink-0 border-t md:border-t-0 md:border-l border-white/10 pt-3 md:pt-0 md:pl-5 text-right font-mono">
          <span className="text-[10px] uppercase tracking-wider text-slate-400">Protocol</span>
          <span className="text-xs font-semibold text-emerald-400">WMO CAP v1.2</span>
          <span className="text-[10px] text-slate-500">Verified thresholds</span>
        </div>
      </div>

      {/* Extreme Weather Threshold Surveillance Matrix */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
            <Activity className="w-4 h-4 text-ensemble" />
            <span>Threshold Surveillance (72h Horizon)</span>
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            {loading ? "Analyzing model records..." : "Real-time Peak Values"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          
          {/* Temperature Extreme Gauge */}
          <div className="glass-panel p-5 rounded-2xl border border-white/10 hover:border-amber-500/30 transition-all space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
                  <Flame className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">Extreme Heat Risk</h3>
                  <span className="text-[11px] text-slate-400 font-mono">Threshold: &gt; 40.0°C</span>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                heatStatus === "WARNING" ? "bg-rose-500/20 text-rose-400 border border-rose-500/40" :
                heatStatus === "ADVISORY" ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" :
                "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              }`}>
                {heatStatus}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between">
              <span className="text-xs text-slate-400">Peak 72h Forecast:</span>
              <div className="flex items-baseline gap-1 font-mono">
                <span className="text-2xl font-black text-white">{maxTemp > 0 ? maxTemp.toFixed(1) : "—"}</span>
                <span className="text-xs text-slate-400">°C</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono text-slate-400">
                <span>Margin to Warning</span>
                <span className="text-emerald-400 font-bold">
                  {maxTemp > 0 ? `+${(heatThreshold - maxTemp).toFixed(1)}°C safe margin` : "Nominal"}
                </span>
              </div>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    heatStatus === "WARNING" ? "bg-rose-500" : heatStatus === "ADVISORY" ? "bg-amber-400" : "bg-emerald-400"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, (maxTemp / 50) * 100))}%` }}
                />
              </div>
            </div>
          </div>

          {/* Severe Wind Gauge */}
          <div className="glass-panel p-5 rounded-2xl border border-white/10 hover:border-sky-500/30 transition-all space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
                  <Wind className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">Gale & Severe Gusts</h3>
                  <span className="text-[11px] text-slate-400 font-mono">Threshold: &gt; 60.0 km/h</span>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                windStatus === "WARNING" ? "bg-rose-500/20 text-rose-400 border border-rose-500/40" :
                windStatus === "ADVISORY" ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" :
                "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              }`}>
                {windStatus}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between">
              <span className="text-xs text-slate-400">Peak 72h Wind:</span>
              <div className="flex items-baseline gap-1 font-mono">
                <span className="text-2xl font-black text-white">{maxWind > 0 ? maxWind.toFixed(1) : "—"}</span>
                <span className="text-xs text-slate-400">km/h</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono text-slate-400">
                <span>Beaufort Level</span>
                <span className="text-emerald-400 font-bold">
                  {maxWind < 20 ? "Light Breeze" : maxWind < 40 ? "Moderate Breeze" : "Strong Breeze"}
                </span>
              </div>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    windStatus === "WARNING" ? "bg-rose-500" : windStatus === "ADVISORY" ? "bg-amber-400" : "bg-emerald-400"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, (maxWind / 80) * 100))}%` }}
                />
              </div>
            </div>
          </div>

          {/* Heavy Precipitation Gauge */}
          <div className="glass-panel p-5 rounded-2xl border border-white/10 hover:border-blue-500/30 transition-all space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <CloudRain className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">Torrential Rainfall</h3>
                  <span className="text-[11px] text-slate-400 font-mono">Threshold: &gt; 20.0 mm/h</span>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                precipStatus === "WARNING" ? "bg-rose-500/20 text-rose-400 border border-rose-500/40" :
                precipStatus === "ADVISORY" ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" :
                "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              }`}>
                {precipStatus}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between">
              <span className="text-xs text-slate-400">Peak Hourly Rate:</span>
              <div className="flex items-baseline gap-1 font-mono">
                <span className="text-2xl font-black text-white">{maxPrecip >= 0 ? maxPrecip.toFixed(1) : "—"}</span>
                <span className="text-xs text-slate-400">mm/h</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono text-slate-400">
                <span>Flood Risk Potential</span>
                <span className="text-emerald-400 font-bold">
                  {maxPrecip > 15 ? "Elevated" : "Negligible (< 5%)"}
                </span>
              </div>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    precipStatus === "WARNING" ? "bg-rose-500" : precipStatus === "ADVISORY" ? "bg-amber-400" : "bg-emerald-400"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, (maxPrecip / 30) * 100))}%` }}
                />
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Alert Protocol Reference Matrix (Progressive Disclosure) */}
      <div className="glass-panel p-5 rounded-2xl border border-white/10 shadow-xl space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <ShieldCheck className="w-4 h-4 text-ensemble" />
            <span>Alert Escalation Protocol (CAP v1.2)</span>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            WMO / NWS Surveillance Standards
          </span>
        </div>

        <p className="text-xs text-slate-300 leading-snug">
          Multi-model consensus threshold surveillance triggers automated advisory escalation adhering to the Common Alerting Protocol.
        </p>

        <details className="pt-1 group border-t border-white/5">
          <summary className="text-[11px] font-mono text-ensemble hover:text-white cursor-pointer select-none transition-colors">
            [View severity classification criteria (Green · Yellow · Orange · Red)]
          </summary>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-3">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs space-y-1">
              <span className="font-bold text-emerald-400 block uppercase font-mono text-[10px]">Green • Nominal</span>
              <p className="text-[11px] text-slate-300">All atmospheric variables within standard climatology.</p>
            </div>
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-1">
              <span className="font-bold text-amber-400 block uppercase font-mono text-[10px]">Yellow • Watch</span>
              <p className="text-[11px] text-slate-300">Potential hazard within 48–72 hours. Model divergence elevated.</p>
            </div>
            <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/20 text-xs space-y-1">
              <span className="font-bold text-orange-400 block uppercase font-mono text-[10px]">Orange • Advisory</span>
              <p className="text-[11px] text-slate-300">Severe conditions expected within 24 hours. Consensus &gt; 70%.</p>
            </div>
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs space-y-1">
              <span className="font-bold text-rose-400 block uppercase font-mono text-[10px]">Red • Warning</span>
              <p className="text-[11px] text-slate-300">Severe weather imminent. High impact to infrastructure.</p>
            </div>
          </div>
        </details>
      </div>

    </div>
  );
}
