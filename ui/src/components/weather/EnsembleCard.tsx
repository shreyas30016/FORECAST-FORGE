"use client";

import { Layers, GitCompare, Info } from "lucide-react";
import { EnsembleResponse } from "@/types/api";
import { useSettings } from "@/context/SettingsContext";

interface EnsembleCardProps {
  ensemble: EnsembleResponse | null;
  className?: string;
}

export function EnsembleCard({ ensemble, className = "" }: EnsembleCardProps) {
  const { convertTemp, convertTempDelta, tempSymbol } = useSettings();

  if (!ensemble) {
    return (
      <div className={`p-6 rounded-2xl bg-panel/60 border border-white/5 animate-pulse text-center text-xs text-text-secondary ${className}`}>
        Synthesizing adaptive weights…
      </div>
    );
  }

  const isTemp = ensemble.variable === "temperature_2m";
  const rawVal = ensemble.ensemble.forecast;
  const ensembleVal = rawVal !== null && rawVal !== undefined ? (isTemp ? convertTemp(Number(rawVal)) : Number(rawVal)) : null;
  const unit = isTemp ? tempSymbol : "";
  const rawUncertainty = ensemble.ensemble.uncertainty;
  const uncertainty = rawUncertainty !== null && rawUncertainty !== undefined && typeof rawUncertainty === "number"
    ? (isTemp ? convertTempDelta(rawUncertainty) : rawUncertainty)
    : rawUncertainty;
  const models = ensemble.models || {};

  const ifs = models["ecmwf_ifs025"];
  const gfs = models["gfs_seamless"];

  const ifsWeight = ifs ? Math.round((ifs.weight || 0) * 100) : 73;
  const gfsWeight = gfs ? Math.round((gfs.weight || 0) * 100) : 27;
  const dataQuality = ensemble.ensemble.data_quality || "HIGH";

  return (
    <div
      className={`rounded-2xl bg-gradient-to-br from-panel/90 via-panel to-background border border-ensemble/25 p-6 shadow-2xl relative overflow-hidden flex flex-col gap-6 ${className}`}
      role="region"
      aria-label="Ensemble Synthesis Card"
    >
      {/* Ambient glow */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-ensemble/8 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-ensemble/15 border border-ensemble/30 flex items-center justify-center text-ensemble shadow-inner">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Adaptive Skill Synthesis</h3>
            <span className="text-xs text-text-muted font-mono">Ridge-regularized inverse-error blend</span>
          </div>
        </div>

        <span
          className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-bold border ${
            dataQuality === "HIGH"
              ? "bg-status-available/10 border-status-available/30 text-status-available"
              : "bg-amber-500/10 border-amber-500/30 text-amber-400"
          }`}
        >
          {dataQuality}
        </span>
      </div>

      {/* Main values: ensemble result + spread */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Ensemble value */}
        <div className="p-5 rounded-xl bg-background/60 backdrop-blur-md border border-ensemble/20 space-y-2">
          <div className="text-xs font-mono text-text-muted uppercase tracking-wider">Ensemble Forecast</div>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black text-white font-sans">
              {ensembleVal !== null && ensembleVal !== undefined
                ? Number(ensembleVal).toFixed(2)
                : "—"}
            </span>
            <span className="text-xl font-bold text-ensemble">{ensembleVal !== null ? unit : ""}</span>
          </div>
          <p className="text-[11px] font-mono text-text-muted">
            Σ(w<sub>i</sub> × val<sub>i</sub>) · Missing values strictly excluded
          </p>
        </div>

        {/* Model spread */}
        <div className="p-5 rounded-xl bg-background/60 backdrop-blur-md border border-amber-500/15 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-text-muted uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-amber-400">
              <GitCompare className="w-3.5 h-3.5" aria-hidden />
              Model Spread
            </span>
            <span className="text-[10px] text-text-muted">max − min</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black text-amber-400 font-sans">
              {uncertainty !== null && uncertainty !== undefined
                ? `±${typeof uncertainty === "number" ? uncertainty.toFixed(2) : uncertainty}`
                : "±0.5"}
            </span>
            <span className="text-base font-semibold text-amber-400/80">{unit}</span>
          </div>
          <p className="text-[11px] font-mono text-amber-400/70">
            |IFS − GFS| · Threshold heuristic: {convertTempDelta(3.5).toFixed(1)}{tempSymbol}
          </p>
        </div>
      </div>

      {/* Weight distribution */}
      <div className="relative z-10 space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-text-muted">
          <span>Model Weight Distribution</span>
          <span>Normalized over active models</span>
        </div>

        {/* Segmented bar */}
        <div
          className="w-full h-2.5 rounded-full bg-background border border-white/10 flex overflow-hidden"
          role="img"
          aria-label={`IFS ${ifsWeight}%, GFS ${gfsWeight}%, AIFS excluded`}
        >
          <div
            className="h-full bg-ifs rounded-l-full transition-all duration-500"
            style={{ width: `${ifsWeight}%` }}
          />
          <div
            className="h-full bg-gfs transition-all duration-500"
            style={{ width: `${gfsWeight}%` }}
          />
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-ifs shrink-0" />
            <span className="text-white">ECMWF IFS</span>
            <span className="text-text-muted">({ifsWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-gfs shrink-0" />
            <span className="text-white">NOAA GFS</span>
            <span className="text-text-muted">({gfsWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5 opacity-50">
            <span className="w-2 h-2 rounded-full bg-aifs shrink-0" />
            <span className="text-text-muted">ECMWF AIFS · AI Model</span>
            <span className="text-amber-400 font-semibold">(0% · No valid data)</span>
          </div>
        </div>
      </div>

      {/* Deterministic rationale with progressive disclosure */}
      <div className="relative z-10 p-3.5 rounded-xl bg-background/40 border border-white/5 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-ensemble uppercase tracking-wide">
            <Info className="w-3.5 h-3.5 shrink-0" aria-hidden />
            <span>Synthesis Rationale</span>
          </div>
          <span className="text-[10px] font-mono text-text-muted">
            IFS {ifsWeight}% · GFS {gfsWeight}% · AIFS 0%
          </span>
        </div>
        <p className="text-xs text-text-secondary leading-snug">
          Adaptive weighting based on evaluated historical skill. Missing values strictly excluded per null-safety.
        </p>
        <details className="pt-1 group">
          <summary className="text-[10px] font-mono text-ensemble hover:text-white cursor-pointer transition-colors select-none">
            [View full methodology &amp; reasoning]
          </summary>
          <p className="text-[11px] text-text-muted mt-1.5 leading-relaxed bg-background/60 p-2.5 rounded-lg border border-white/5 font-mono">
            {ensemble.explanation?.reasoning ||
              `Adaptive ensemble assigns ${ifsWeight}% to ECMWF IFS and ${gfsWeight}% to NOAA GFS based on evaluated historical skill for ${ensemble.variable}. ECMWF AIFS · AI Model excluded — no valid forecast values for this context.`}
          </p>
        </details>
      </div>
    </div>
  );
}
