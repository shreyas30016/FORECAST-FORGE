"use client";

import { ShieldAlert, CheckCircle2, Wind, Droplets, CloudRain, AlertCircle } from "lucide-react";
import { useSettings } from "@/context/SettingsContext";

type ModelId = "ecmwf_ifs025" | "gfs_seamless" | "ecmwf_aifs025";

interface ModelCardProps {
  id: ModelId;
  name: string;
  provider: string;
  status: "AVAILABLE" | "UNAVAILABLE" | "DEGRADED" | "NO_VALID_DATA";
  value: number | null;
  unit?: string;
  weight: number;
  precipitation?: number | null;
  windSpeed?: number | null;
  humidity?: number | null;
  skill?: {
    mae?: number | null;
    rmse?: number | null;
  };
  reason?: string | null;
}

export function ModelCard({
  id,
  name,
  provider,
  status,
  value,
  unit = "°C",
  weight,
  precipitation,
  windSpeed,
  humidity,
  skill,
  reason,
}: ModelCardProps) {
  const { convertTemp, tempSymbol, convertWind, windSymbol } = useSettings();
  const isIFS = id === "ecmwf_ifs025";
  const isGFS = id === "gfs_seamless";
  const isAIFS = id === "ecmwf_aifs025";
  const isAvailable = status === "AVAILABLE" || status === "DEGRADED";
  const isNoData = status === "NO_VALID_DATA";

  const accentBg = isIFS ? "bg-ifs" : isGFS ? "bg-gfs" : "bg-aifs";
  const accentText = isIFS ? "text-sky-400" : isGFS ? "text-orange-400" : "text-violet-400";
  const accentBorder = isIFS ? "border-sky-500/20" : isGFS ? "border-orange-500/20" : "border-violet-500/20";

  return (
    <div
      className={`rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden transition-all duration-300 ${
        isAvailable
          ? `bg-panel/60 hover:bg-panel/80 border ${accentBorder} shadow-lg backdrop-blur-md`
          : "bg-panel/20 border border-white/5 opacity-75 backdrop-blur-sm"
      }`}
      aria-label={`${name} model card — ${status}`}
    >
      {/* Ambient identity glow */}
      {isAvailable && (
        <div
          className={`absolute top-0 right-0 w-40 h-40 blur-3xl opacity-[0.12] -mr-12 -mt-12 rounded-full pointer-events-none ${accentBg}`}
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-2 relative z-10">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full shrink-0 ${accentBg}`} />
            <h3 className="font-bold text-base text-white tracking-tight">{name}</h3>
          </div>
          <span className="text-xs text-text-muted block">{provider}</span>
        </div>

        {isAvailable ? (
          <CheckCircle2 className="w-4 h-4 text-status-available opacity-70 shrink-0" aria-label="Available" />
        ) : isNoData ? (
          <AlertCircle className="w-4 h-4 text-amber-400 opacity-80 shrink-0" aria-label="No valid data" />
        ) : (
          <ShieldAlert className="w-4 h-4 text-status-unavailable opacity-70 shrink-0" aria-label="Unavailable" />
        )}
      </div>

      {/* Primary value + weight */}
      <div className="flex items-end justify-between relative z-10">
        <div className="flex items-start gap-1">
          <span className={`text-4xl sm:text-5xl font-black tracking-tighter ${isAvailable ? "text-white" : "text-text-muted"}`}>
            {value !== null && value !== undefined 
              ? (unit === "°C" ? convertTemp(Number(value)).toFixed(1) : value) 
              : "—"}
          </span>
          <span className="text-base font-semibold text-text-secondary mt-1.5">
            {value !== null ? (unit === "°C" ? tempSymbol : unit) : ""}
          </span>
        </div>

        <div className="text-right flex flex-col items-end gap-0.5">
          <span className={`text-2xl font-black ${isAvailable ? accentText : "text-text-muted"}`}>
            {isAvailable ? `${Math.round(weight * 100)}%` : "0%"}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-text-muted font-mono">
            {isAvailable ? "Ensemble Weight" : "Excluded"}
          </span>
        </div>
      </div>

      {/* Secondary metrics or exclusion notice */}
      {isAvailable ? (
        <div className="grid grid-cols-3 gap-2 bg-background/30 rounded-xl p-3 relative z-10">
          <div className="flex flex-col items-center gap-1 text-center">
            <CloudRain className="w-3.5 h-3.5 text-sky-400" aria-hidden />
            <div className="text-sm font-bold text-white">
              {precipitation != null ? precipitation : 0}
              <span className="text-[10px] text-text-muted font-normal ml-0.5">mm</span>
            </div>
          </div>
          <div className="flex flex-col items-center gap-1 text-center">
            <Wind className="w-3.5 h-3.5 text-cyan-400" aria-hidden />
            <div className="text-sm font-bold text-white">
              {windSpeed != null ? convertWind(windSpeed).toFixed(1) : "—"}
              <span className="text-[10px] text-text-muted font-normal ml-0.5">{windSymbol}</span>
            </div>
          </div>
          <div className="flex flex-col items-center gap-1 text-center">
            <Droplets className="w-3.5 h-3.5 text-blue-400" aria-hidden />
            <div className="text-sm font-bold text-white">
              {humidity != null ? humidity : "—"}
              <span className="text-[10px] text-text-muted font-normal ml-0.5">%</span>
            </div>
          </div>
        </div>
      ) : isNoData && isAIFS ? (
        <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/15 text-xs space-y-1 relative z-10">
          <div className="font-semibold text-amber-400 text-[11px]">NO VALID DATA</div>
          <p className="text-text-muted text-[11px] leading-snug">
            Excluded from current deterministic ensemble. Null-safety protocol active.
          </p>
          {reason && (
            <details className="mt-1">
              <summary className="text-[10px] text-text-muted cursor-pointer hover:text-white transition-colors">
                Technical reason
              </summary>
              <p className="text-[10px] text-text-muted mt-1 leading-relaxed">{reason}</p>
            </details>
          )}
        </div>
      ) : (
        <div className="p-3 rounded-xl bg-status-unavailable/5 border border-status-unavailable/15 text-xs space-y-1 relative z-10">
          <div className="font-semibold text-status-unavailable text-[11px]">PROVIDER UNAVAILABLE</div>
          <p className="text-text-muted text-[11px] leading-snug">
            {reason || "Network error or provider failure for this coordinate."}
          </p>
        </div>
      )}

      {/* Historical skill footnote */}
      <div className="flex items-center justify-between text-[11px] text-text-muted relative z-10 font-mono">
        <span>Historical Error</span>
        {skill?.mae != null ? (
          <span>
            MAE <span className="text-text-secondary">{skill.mae}</span>
            {skill?.rmse != null && <> · RMSE <span className="text-text-secondary">{skill.rmse}</span></>}
          </span>
        ) : (
          <span className="opacity-40 italic">No skill samples</span>
        )}
      </div>
    </div>
  );
}
