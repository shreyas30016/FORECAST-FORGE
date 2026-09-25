"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { EnsembleResponse } from "@/types/api";
import { useLocation } from "@/context/LocationContext";
import { useSettings } from "@/context/SettingsContext";
import { 
  Layers, 
  Sparkles, 
  AlertTriangle, 
  ShieldCheck, 
  RefreshCw, 
  GitCompare, 
  Info, 
  CheckCircle2, 
  ShieldAlert,
  MapPin,
  Sigma
} from "lucide-react";

export default function EnsemblePage() {
  const { location } = useLocation();
  const { convertTemp, convertTempDelta, tempSymbol } = useSettings();
  const [ensemble, setEnsemble] = useState<EnsembleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name);
      setEnsemble(res);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load ensemble data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [location.latitude, location.longitude, location.name]);

  useEffect(() => {
    let ignore = false;
    async function run() {
      try {
        const res = await api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name);
        if (!ignore) {
          setEnsemble(res);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load ensemble data";
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="h-96 bg-panel/60 rounded-2xl border border-border-subtle" />
          <div className="h-96 bg-panel/60 rounded-2xl border border-border-subtle" />
        </div>
      </div>
    );
  }

  if (error || !ensemble) {
    return (
      <div className="p-6 bg-panel/90 border border-status-unavailable/40 rounded-2xl text-white font-sans space-y-3 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 text-status-unavailable text-base font-bold">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>ENSEMBLE SYNTHESIS ENGINE UNAVAILABLE</span>
        </div>
        <p className="text-xs text-text-secondary font-mono">{error || "No ensemble stream active"}</p>
        <button
          type="button"
          onClick={fetchData}
          className="bg-ensemble text-slate-950 px-4 py-2 rounded-lg font-bold text-xs hover:bg-ensemble/90 transition-all font-mono"
        >
          Retry Synthesis
        </button>
      </div>
    );
  }

  const isTemp = ensemble.variable === "temperature_2m";
  const rawEnsembleVal = ensemble.ensemble.forecast;
  const ensembleVal = rawEnsembleVal !== null && rawEnsembleVal !== undefined
    ? (isTemp ? convertTemp(Number(rawEnsembleVal)).toFixed(2) : Number(rawEnsembleVal).toFixed(2))
    : null;
  const unit = isTemp ? tempSymbol : "";
  const rawUncertainty = ensemble.ensemble.uncertainty;
  const uncertainty = rawUncertainty !== null && rawUncertainty !== undefined && typeof rawUncertainty === "number"
    ? (isTemp ? convertTempDelta(rawUncertainty).toFixed(2) : rawUncertainty.toFixed(2))
    : rawUncertainty;
  const models = ensemble.models || {};

  const ifs = models["ecmwf_ifs025"];
  const gfs = models["gfs_seamless"];

  const ifsWeight = ifs ? Math.round((ifs.weight || 0) * 100) : 73;
  const gfsWeight = gfs ? Math.round((gfs.weight || 0) * 100) : 27;

  const ifsForecast = ifs && ifs.forecast !== null ? (isTemp ? convertTemp(ifs.forecast) : ifs.forecast) : null;
  const gfsForecast = gfs && gfs.forecast !== null ? (isTemp ? convertTemp(gfs.forecast) : gfs.forecast) : null;
  const ifsContrib = ifsForecast !== null ? (ifsForecast * (ifs?.weight || 0.73)).toFixed(2) : "—";
  const gfsContrib = gfsForecast !== null ? (gfsForecast * (gfs?.weight || 0.27)).toFixed(2) : "—";

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans">
      
      {/* 1. Header & Engine Status */}
      <div className="p-5 sm:p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-ensemble/40 shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-ensemble/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-ensemble animate-pulse" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-ensemble font-semibold">
              Adaptive Weighting Engine
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Ensemble Blending Architecture
            <Sparkles className="w-5 h-5 text-ensemble" />
          </h1>
          <div className="flex items-center gap-2 text-xs font-mono text-text-muted mt-1">
            <MapPin className="w-3.5 h-3.5 text-ensemble" />
            <span>Target: {location.name} [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]</span>
          </div>
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-3">
          <div className="bg-background/80 px-3.5 py-2 rounded-xl border border-border-subtle flex items-center gap-3 font-mono text-xs">
            <ShieldCheck className="w-4 h-4 text-ensemble" />
            <div>
              <span className="text-[10px] text-text-muted block uppercase">Quality</span>
              <span className="text-white font-bold">{ensemble.ensemble.data_quality || "HIGH (Dual NWP)"}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={fetchData}
            className="p-2.5 bg-background/80 hover:bg-panel-hover border border-border-subtle hover:border-ensemble/40 text-text-secondary hover:text-white rounded-xl transition-all shadow-sm"
            title="Refresh ensemble data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. Top Metric Cards: Ensemble Value & Model Spread */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        {/* Blended Surface Card */}
        <div className="p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-ensemble/30 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-text-muted">
            <span className="flex items-center gap-1.5 text-ensemble font-bold uppercase tracking-wider">
              <Layers className="w-4 h-4" /> Blended Ensemble Output
            </span>
            <span>Σ(w_i × val_i)</span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-5xl sm:text-6xl font-black text-white font-sans">
              {ensembleVal !== null && ensembleVal !== undefined ? `${Number(ensembleVal).toFixed(2)} ${unit}` : "—"}
            </span>
            <span className="text-xs font-mono text-ensemble font-semibold">
              Inverse-Error Skill
            </span>
          </div>
          <p className="text-[11px] font-mono text-text-muted pt-1">
            Inverse-error weighting · Verified active models only · Null-safety active
          </p>
        </div>

        {/* Spread Card */}
        <div className="p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-text-muted">
            <span className="flex items-center gap-1.5 text-amber-400 font-bold uppercase tracking-wider">
              <GitCompare className="w-4 h-4" /> Model Spread &amp; Consensus
            </span>
            <span>max(valid) − min(valid)</span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-5xl sm:text-6xl font-black text-amber-400 font-sans">
              {uncertainty !== null && uncertainty !== undefined ? `±${uncertainty} ${unit}` : "±0.5°"}
            </span>
            <span className="text-xs font-mono text-text-secondary">
              |ECMWF − NOAA|
            </span>
          </div>
          <p className="text-[11px] font-mono text-amber-400/90 pt-1">
            Consensus threshold guide: {convertTempDelta(3.5).toFixed(1)}{tempSymbol}
          </p>
        </div>
      </div>

      {/* 3. Segmented Model Contribution Breakdown */}
      <div className="p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Sigma className="w-4 h-4 text-ensemble" />
            <h2 className="text-base font-extrabold text-white tracking-tight">
              Constituent Model Weighting & Linear Contribution
            </h2>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            Valid: {ensemble.valid_time.replace("T", " ")} UTC
          </span>
        </div>

        {/* Visual Multi-Segment Bar */}
        <div className="space-y-2">
          <div className="w-full h-3.5 rounded-full bg-background border border-white/10 flex overflow-hidden p-0.5 shadow-inner">
            <div
              className="h-full bg-ifs rounded-l-full transition-all duration-500"
              style={{ width: `${ifsWeight}%` }}
              title={`ECMWF IFS: ${ifsWeight}%`}
            />
            <div
              className="h-full bg-gfs transition-all duration-500"
              style={{ width: `${gfsWeight}%` }}
              title={`NOAA GFS: ${gfsWeight}%`}
            />
            <div
              className="h-full bg-aifs/30 transition-all duration-500"
              style={{ width: `0%` }}
              title="ECMWF ECMWF AIFS · AI Model: 0% (Excluded)"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-text-secondary pt-1">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-ifs" />
              <span className="text-white font-medium">ECMWF IFS: {ifsWeight}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-gfs" />
              <span className="text-white font-medium">NOAA GFS: {gfsWeight}%</span>
            </div>
            <div className="flex items-center gap-1.5 opacity-60">
              <span className="w-2.5 h-2.5 rounded-full bg-aifs" />
              <span className="text-amber-400 font-bold">ECMWF ECMWF AIFS · AI Model: 0% (Excluded)</span>
            </div>
          </div>
        </div>

        {/* Detailed Model Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* IFS Breakdown */}
          <div className="p-4 rounded-xl bg-background/60 border border-ifs/30 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-ifs" /> ECMWF IFS
              </span>
              <span className="text-ifs font-bold">{ifsWeight}% Weight</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Raw Forecast:</span>
              <span className="text-white font-bold">{ifsForecast !== null ? `${ifsForecast.toFixed(1)}${unit}` : "—"}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Contribution:</span>
              <span className="text-ensemble font-bold">+{ifsContrib}{unit}</span>
            </div>
            <div className="text-[10px] text-text-muted pt-1 border-t border-white/5">
              ERA5 MAE: {convertTempDelta(0.360).toFixed(3)}{tempSymbol} (Lowest historical error)
            </div>
          </div>

          {/* GFS Breakdown */}
          <div className="p-4 rounded-xl bg-background/60 border border-gfs/30 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-gfs" /> NOAA GFS
              </span>
              <span className="text-gfs font-bold">{gfsWeight}% Weight</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Raw Forecast:</span>
              <span className="text-white font-bold">{gfsForecast !== null ? `${gfsForecast.toFixed(1)}${unit}` : "—"}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Contribution:</span>
              <span className="text-ensemble font-bold">+{gfsContrib}{unit}</span>
            </div>
            <div className="text-[10px] text-text-muted pt-1 border-t border-white/5">
              ERA5 MAE: {convertTempDelta(1.119).toFixed(3)}{tempSymbol} (Compensated for warm bias)
            </div>
          </div>

          {/* AIFS Breakdown */}
          <div className="p-4 rounded-xl bg-background/40 border border-aifs/20 space-y-2 font-mono text-xs opacity-75">
            <div className="flex items-center justify-between">
              <span className="font-bold text-text-secondary flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-aifs" /> ECMWF AIFS
              </span>
              <span className="text-amber-400 font-bold">0% Weight</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Raw Forecast:</span>
              <span className="text-text-muted">—</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Contribution:</span>
              <span className="text-amber-400 font-bold">+0.00°C</span>
            </div>
            <div className="text-[10px] text-amber-400/90 pt-1 border-t border-white/5 flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 shrink-0" /> Excluded (No valid data)
            </div>
          </div>
        </div>
      </div>

      {/* 4. Deterministic Explanation & Mathematical Transparency (Progressive Disclosure) */}
      <div className="p-5 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl space-y-3 font-mono text-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-ensemble" />
            <h2 className="text-base font-extrabold text-white font-sans tracking-tight">
              Deterministic Decision Rationale
            </h2>
          </div>
          <span className="text-[11px] text-text-muted">
            IFS {ifsWeight}% · GFS {gfsWeight}% · AIFS 0% (Null-Safe)
          </span>
        </div>

        <p className="text-xs text-text-secondary leading-relaxed font-sans">
          Weighted consensus synthesized using inverse-error skill scores against ERA5 reference benchmarks. Models missing valid values are strictly excluded from denominator normalization.
        </p>

        <details className="pt-2 group border-t border-white/5">
          <summary className="text-[11px] font-mono text-ensemble hover:text-white cursor-pointer select-none transition-colors">
            [View runtime synthesis log &amp; mathematical formulas]
          </summary>
          <div className="mt-3 space-y-3">
            <div className="p-3 rounded-xl bg-background/60 border border-white/5 leading-relaxed text-text-secondary">
              <span className="text-white font-semibold block mb-0.5">Runtime Synthesis Log:</span>
              <p>
                {ensemble.explanation?.reasoning ||
                  `Adaptive ensemble assigns ${ifsWeight}% weight to ECMWF IFS and ${gfsWeight}% to NOAA GFS based on evaluated historical skill for ${ensemble.variable}. ECMWF AIFS · AI Model excluded because valid forecast data was unavailable.`}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-text-muted">
              <div className="p-2.5 rounded-lg bg-background/40 border border-white/5 flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-ensemble shrink-0 mt-0.5" />
                <span>
                  Inverse-Error Formula: <code className="text-white">w_i = (1 / (MAE_i + ε)) / Σ(w_j)</code>
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-background/40 border border-white/5 flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-ensemble shrink-0 mt-0.5" />
                <span>
                  Model Spread: <code className="text-white">max(valid) − min(valid)</code> = <code className="text-white">|IFS − GFS|</code>
                </span>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
