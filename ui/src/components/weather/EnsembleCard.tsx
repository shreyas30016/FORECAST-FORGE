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

  // Categorize models by weight state:
  // 1. Contributing: AVAILABLE with weight > 0
  // 2. Available but no weighting: AVAILABLE with weight === 0 or weight === null
  // 3. Excluded: NO_VALID_DATA or other unavailable status
  const contributingModels = Object.entries(models)
    .filter(([_, m]) => (m.status === "AVAILABLE" || m.status === "DEGRADED") && m.weight !== null && m.weight > 0)
    .sort((a, b) => (b[1].weight ?? 0) - (a[1].weight ?? 0));

  const availableNoWeight = Object.entries(models)
    .filter(([_, m]) => (m.status === "AVAILABLE" || m.status === "DEGRADED") && (m.weight === null || m.weight === 0));

  const unavailableModels = Object.entries(models)
    .filter(([_, m]) => m.status !== "AVAILABLE" && m.status !== "DEGRADED");

  const dataQuality = ensemble.ensemble.data_quality || "HIGH";

  const getModelColor = (modelId: string) => {
    if (modelId.includes("ifs")) return "bg-ifs";
    if (modelId.includes("gfs")) return "bg-gfs";
    if (modelId.includes("aifs")) return "bg-aifs";
    return "bg-gray-400";
  };

  const formatModelName = (modelId: string) => {
    if (modelId === "ecmwf_ifs025") return "ECMWF IFS";
    if (modelId === "gfs_seamless") return "NOAA GFS";
    if (modelId === "ecmwf_aifs025") return "ECMWF AIFS";
    return modelId;
  };

  return (
    <div
      className={`rounded-2xl bg-gradient-to-br from-panel/90 via-panel to-background border border-ensemble/25 p-6 shadow-2xl relative overflow-hidden flex flex-col gap-6 ${className}`}
      role="region"
      aria-label="Ensemble Synthesis Card"
    >
      <div className="absolute top-0 right-0 w-72 h-72 bg-ensemble/8 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      <div className="relative z-10 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-ensemble/15 border border-ensemble/30 flex items-center justify-center text-ensemble shadow-inner">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Adaptive Skill Synthesis</h3>
            <span className="text-xs text-text-muted font-mono">
              {ensemble.ensemble.method === "ADAPTIVE" ? "Ridge-regularized adaptive blend"
                : ensemble.ensemble.method === "INVERSE_ERROR" ? "Inverse-error weighted blend"
                : ensemble.ensemble.method === "EQUAL_WEIGHT" ? "Equal-weight consensus blend"
                : "No weighted ensemble available"}
            </span>
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

      <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-4">
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
            {ensemble.ensemble.method !== "UNAVAILABLE"
              ? "Σ(wᵢ × valᵢ) · Missing values strictly excluded"
              : "Insufficient model data for weighted synthesis"}
          </p>
        </div>

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
                : "—"}
            </span>
            <span className="text-base font-semibold text-amber-400/80">{uncertainty !== null && uncertainty !== undefined ? unit : ""}</span>
          </div>
          <p className="text-[11px] font-mono text-amber-400/70">
            Model disagreement
          </p>
        </div>
      </div>

      <div className="relative z-10 space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-text-muted">
          <span>Model Weight Distribution</span>
          <span>{contributingModels.length > 0 ? "Normalized over contributing models" : "No weights assigned"}</span>
        </div>

        {contributingModels.length > 0 && (
          <div
            className="w-full h-2.5 rounded-full bg-background border border-white/10 flex overflow-hidden"
            role="img"
            aria-label="Weight Distribution"
          >
            {contributingModels.map(([id, m]) => (
              <div
                key={id}
                className={`h-full ${getModelColor(id)} transition-all duration-500 border-r border-background/20 last:border-0`}
                style={{ width: `${(m.weight ?? 0) * 100}%` }}
                title={`${formatModelName(id)}: ${Math.round((m.weight ?? 0) * 100)}%`}
              />
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-mono">
          {contributingModels.map(([id, m]) => (
            <div key={id} className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full shrink-0 ${getModelColor(id)}`} />
              <span className="text-white">{formatModelName(id)}</span>
              <span className="text-text-muted">({Math.round((m.weight ?? 0) * 100)}%)</span>
            </div>
          ))}
          {availableNoWeight.map(([id]) => (
            <div key={id} className="flex items-center gap-1.5 opacity-60">
              <span className={`w-2 h-2 rounded-full shrink-0 ${getModelColor(id)}`} />
              <span className="text-text-muted">{formatModelName(id)}</span>
              <span className="text-slate-400 font-semibold">(Available · No current weight)</span>
            </div>
          ))}
          {unavailableModels.map(([id, m]) => (
            <div key={id} className="flex items-center gap-1.5 opacity-50">
              <span className={`w-2 h-2 rounded-full shrink-0 ${getModelColor(id)}`} />
              <span className="text-text-muted">{formatModelName(id)}</span>
              <span className="text-amber-400 font-semibold">({m.status === "NO_VALID_DATA" ? "No valid data" : m.status})</span>
            </div>
          ))}
        </div>
      </div>

      <div className="relative z-10 p-3.5 rounded-xl bg-background/40 border border-white/5 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-ensemble uppercase tracking-wide">
            <Info className="w-3.5 h-3.5 shrink-0" aria-hidden />
            <span>Synthesis Rationale</span>
          </div>
        </div>
        <p className="text-xs text-text-secondary leading-snug">
          Adaptive weighting based on evaluated historical skill. Missing values strictly excluded per null-safety.
        </p>
        {ensemble.explanation?.reasoning && (
          <details className="pt-1 group">
            <summary className="text-[10px] font-mono text-ensemble hover:text-white cursor-pointer transition-colors select-none">
              [View full methodology &amp; reasoning]
            </summary>
            <p className="text-[11px] text-text-muted mt-1.5 leading-relaxed bg-background/60 p-2.5 rounded-lg border border-white/5 font-mono">
              {ensemble.explanation.reasoning}
            </p>
          </details>
        )}
      </div>
    </div>
  );
}
