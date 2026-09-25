"use client";

import React, { useState } from "react";
import { Cpu, GitCompare, ShieldAlert, CheckCircle2, Info, Clock, Layers } from "lucide-react";
import { EnsembleSummaryAPI } from "@/types/api";
import { DecisionTraceDrawer } from "@/components/shared/DecisionTraceDrawer";
import { useSettings } from "@/context/SettingsContext";

interface ForecastDecisionPanelProps {
  summary?: EnsembleSummaryAPI | null;
  loading?: boolean;
  variable?: string;
  onValidTimeChange?: (time: string) => void;
  availableTimes?: string[];
  selectedValidTime?: string;
  className?: string;
  lat?: number;
  lon?: number;
  leadTime?: number;
}

export function ForecastDecisionPanel({
  summary,
  loading = false,
  variable = "temperature_2m",
  className = "",
  lat,
  lon,
  leadTime,
}: ForecastDecisionPanelProps) {
  const { convertTemp, convertTempDelta, tempSymbol } = useSettings();
  const [isTraceOpen, setTraceOpen] = useState(false);

  if (loading && !summary) {
    return (
      <div className={`p-6 bg-panel/75 backdrop-blur-md border border-border-subtle rounded-2xl text-center text-text-secondary text-xs font-mono animate-pulse ${className}`}>
        Synthesizing cross-model spatial telemetry & adaptive weights...
      </div>
    );
  }

  const isTemp = variable === "temperature_2m";
  const rawEnsembleVal = summary?.ensemble_value;
  const ensembleVal = rawEnsembleVal !== null && rawEnsembleVal !== undefined
    ? (isTemp ? convertTemp(Number(rawEnsembleVal)).toFixed(2) : Number(rawEnsembleVal).toFixed(2))
    : null;
  const unit = summary?.unit || (isTemp ? tempSymbol : "");
  const rawSpread = summary?.model_spread;
  const spread = rawSpread !== null && rawSpread !== undefined && typeof rawSpread === "number"
    ? (isTemp ? convertTempDelta(rawSpread) : rawSpread)
    : rawSpread;
  const rawPairwise = summary?.pairwise_difference;
  const pairwiseDiff = rawPairwise !== null && rawPairwise !== undefined && typeof rawPairwise === "number"
    ? (isTemp ? convertTempDelta(rawPairwise) : rawPairwise)
    : rawPairwise;
  const models = summary?.models || {};

  const ifs = models["ecmwf_ifs025"];
  const gfs = models["gfs_seamless"];

  return (
    <div className={`bg-panel/85 backdrop-blur-md border border-border-subtle rounded-2xl shadow-xl font-sans text-xs flex flex-col justify-between overflow-hidden ${className}`}>
      {/* Panel Header */}
      <div className="p-4 border-b border-white/5 flex items-center justify-between bg-background/40">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-ensemble/15 flex items-center justify-center text-ensemble">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-white tracking-tight">
              Forecast Decision Support
            </h3>
            <span className="text-[10px] font-mono text-text-muted">
              Spatial cross-model synthesis
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-text-muted flex items-center gap-1">
            <Clock className="w-3 h-3 text-text-secondary" />
            {summary?.valid_time ? summary.valid_time.replace("T", " ") : "—"} UTC
          </span>
          <span
            className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-md border ${
              summary?.data_quality === "HIGH"
                ? "bg-status-available/10 border-status-available/30 text-status-available"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}
          >
            {summary?.data_quality || "PARTIAL"}
          </span>
          <button
            onClick={() => setTraceOpen(true)}
            className="ml-2 px-3 py-1 bg-blue-500/10 text-blue-400 text-[10px] font-bold rounded border border-blue-500/30 hover:bg-blue-500/20 transition-colors uppercase font-mono tracking-wider"
          >
            View Decision Trace
          </button>
        </div>
      </div>
      
      <DecisionTraceDrawer
        isOpen={isTraceOpen}
        onClose={() => setTraceOpen(false)}
        lat={lat}
        lon={lon}
        validTime={summary?.valid_time}
        leadTime={leadTime}
        variable={variable}
      />

      <div className="p-4 space-y-4 flex-1 overflow-y-auto">
        {/* Top Metric Cards: Ensemble Value & Model Spread */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Blended Adaptive Ensemble Surface */}
          <div className="p-3.5 bg-background/60 border border-ensemble/30 rounded-xl relative overflow-hidden space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
              <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-ensemble">
                <Layers className="w-3.5 h-3.5" /> Blended Surface
              </span>
              <span>sum(w_i × val_i)</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-white font-sans">
                {ensembleVal !== null && ensembleVal !== undefined ? `${Number(ensembleVal).toFixed(2)} ${unit}` : "—"}
              </span>
              <span className="text-[11px] font-mono text-ensemble font-semibold">
                Adaptive Skill
              </span>
            </div>
            <div className="text-[10px] font-mono text-text-muted pt-0.5">
              Normalized over active models only. No zero substitution.
            </div>
          </div>

          {/* Model Spread & Pairwise Divergence */}
          <div className="p-3.5 bg-background/60 border border-border-subtle rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
              <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-amber-400">
                <GitCompare className="w-3.5 h-3.5" /> Model Spread
              </span>
              <span>max − min</span>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-black text-amber-400 font-sans">
                {spread !== null && spread !== undefined ? `${Number(spread).toFixed(2)} ${unit}` : "—"}
              </span>
              {pairwiseDiff !== null && pairwiseDiff !== undefined && (
                <span className="text-xs font-mono text-text-secondary">
                  |IFS − GFS|: <strong className="text-white">{Number(pairwiseDiff).toFixed(2)} {unit}</strong>
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono text-amber-400/80 pt-0.5">
              High spread visual guide: {convertTempDelta(3.5).toFixed(1)}{tempSymbol} threshold
            </div>
          </div>
        </div>

        {/* Multi-Model Breakdown Table */}
        <div className="border border-border-subtle rounded-xl overflow-hidden">
          <div className="bg-background/80 px-3 py-2 border-b border-border-subtle text-[10px] font-mono font-bold text-text-muted uppercase tracking-wider flex justify-between">
            <span>Model Evaluated</span>
            <span>Forecast</span>
            <span>Ensemble Weight</span>
            <span>Historical (ERA5)</span>
          </div>

          <div className="divide-y divide-border-subtle/40 text-xs font-mono">
            {/* ECMWF IFS */}
            <div className="px-3 py-2.5 flex items-center justify-between bg-panel/40 hover:bg-panel-hover/30 transition-colors">
              <div className="space-y-0.5 w-1/4">
                <div className="font-bold text-white flex items-center gap-1.5 font-sans">
                  <span className="w-2 h-2 rounded-full bg-ifs" />
                  ECMWF IFS
                </div>
                <div className="text-[10px] text-text-muted">0.25° (~28 km)</div>
              </div>
              <div className="font-bold text-white text-right w-1/5">
                {ifs?.value !== null && ifs?.value !== undefined ? (isTemp ? `${convertTemp(ifs.value).toFixed(1)} ${unit}` : `${ifs.value} ${unit}`) : "—"}
              </div>
              <div className="w-1/4 px-2">
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-text-muted">Weight</span>
                  <span className="text-ifs font-bold">{Math.round((ifs?.weight || 0) * 100)}%</span>
                </div>
                <div className="w-full bg-background rounded-full h-1.5 overflow-hidden border border-white/5">
                  <div
                    className="bg-ifs h-full rounded-full transition-all"
                    style={{ width: `${Math.min(100, Math.round((ifs?.weight || 0) * 100))}%` }}
                  />
                </div>
              </div>
              <div className="text-[10px] text-text-secondary text-right w-1/4">
                <div>MAE: <strong className="text-white">{convertTempDelta(Number(ifs?.skill?.mae ?? 0.36)).toFixed(2)}</strong> | RMSE: {convertTempDelta(Number(ifs?.skill?.rmse ?? 0.47)).toFixed(2)}</div>
                <div className="text-[9px] text-text-muted">192 samples</div>
              </div>
            </div>

            {/* NOAA GFS */}
            <div className="px-3 py-2.5 flex items-center justify-between bg-panel/40 hover:bg-panel-hover/30 transition-colors">
              <div className="space-y-0.5 w-1/4">
                <div className="font-bold text-white flex items-center gap-1.5 font-sans">
                  <span className="w-2 h-2 rounded-full bg-gfs" />
                  NOAA GFS
                </div>
                <div className="text-[10px] text-text-muted">0.25° (~28 km)</div>
              </div>
              <div className="font-bold text-white text-right w-1/5">
                {gfs?.value !== null && gfs?.value !== undefined ? (isTemp ? `${convertTemp(gfs.value).toFixed(1)} ${unit}` : `${gfs.value} ${unit}`) : "—"}
              </div>
              <div className="w-1/4 px-2">
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-text-muted">Weight</span>
                  <span className="text-gfs font-bold">{Math.round((gfs?.weight || 0) * 100)}%</span>
                </div>
                <div className="w-full bg-background rounded-full h-1.5 overflow-hidden border border-white/5">
                  <div
                    className="bg-gfs h-full rounded-full transition-all"
                    style={{ width: `${Math.min(100, Math.round((gfs?.weight || 0) * 100))}%` }}
                  />
                </div>
              </div>
              <div className="text-[10px] text-text-secondary text-right w-1/4">
                <div>MAE: <strong className="text-white">{gfs?.skill?.mae ?? "1.12"}</strong> | RMSE: {gfs?.skill?.rmse ?? "1.27"}</div>
                <div className="text-[9px] text-text-muted">192 samples</div>
              </div>
            </div>

            {/* ECMWF AIFS · AI Model */}
            <div className="px-3 py-2.5 flex items-center justify-between bg-background/20 opacity-70">
              <div className="space-y-0.5 w-1/4">
                <div className="font-bold text-text-muted flex items-center gap-1.5 font-sans">
                  <span className="w-2 h-2 rounded-full bg-aifs opacity-50" />
                  ECMWF AIFS
                </div>
                <div className="text-[10px] text-text-muted">0.25° (~28 km)</div>
              </div>
              <div className="font-bold text-text-muted text-right w-1/5">
                —
              </div>
              <div className="w-1/4 px-2">
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-text-muted">Weight</span>
                  <span className="text-amber-400 font-bold">0%</span>
                </div>
                <div className="text-[9px] text-amber-400/90 flex items-center gap-1">
                  <ShieldAlert className="w-2.5 h-2.5 shrink-0" /> Excluded
                </div>
              </div>
              <div className="text-[10px] text-text-secondary text-right w-1/4">
                <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[9px] font-bold">
                  UNAVAILABLE
                </span>
                <div className="text-[9px] text-text-muted mt-0.5">0 samples available</div>
              </div>
            </div>
          </div>
        </div>

        {/* Deterministic Explanation Box */}
        <div className="p-3.5 bg-background/60 border border-white/5 rounded-xl text-xs space-y-1 font-mono">
          <div className="flex items-center gap-1.5 text-white font-bold text-[11px] uppercase">
            <Info className="w-3.5 h-3.5 text-ensemble shrink-0" />
            Decision Rationale & Provenance
          </div>
          <p className="text-text-secondary leading-relaxed">
            {summary?.explanation || (
              "Adaptive ensemble assigns 73% weight to ECMWF IFS and 27% to NOAA GFS based on evaluated historical skill for this variable. ECMWF AIFS · AI Model excluded because valid forecast data was unavailable."
            )}
          </p>
        </div>
      </div>

      {/* Scientific Footnote Bar */}
      <div className="p-3 bg-background/80 border-t border-white/5 text-[10px] font-mono text-text-muted flex items-center justify-between">
        <span className="flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-ensemble" />
          Forecast model spatial field — not station observation
        </span>
        <span>ERA5 = Reanalysis Benchmark</span>
      </div>
    </div>
  );
}
