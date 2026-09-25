"use client";

import { useState } from "react";
import { MapWrapper } from "@/components/maps/MapWrapper";
import { ForecastDecisionPanel } from "@/components/maps/ForecastDecisionPanel";
import { useLocation } from "@/context/LocationContext";
import { EnsembleSummaryAPI } from "@/types/api";
import { Map as MapIcon, Crosshair, Compass, Layers, Sparkles } from "lucide-react";

export default function MapsPage() {
  const { location, presets, setLocation } = useLocation();
  const [summary, setSummary] = useState<EnsembleSummaryAPI | null>(null);
  const [mapLocation, setMapLocation] = useState<{lat: number, lon: number} | undefined>(undefined);
  const [mapLeadTime, setMapLeadTime] = useState<number | undefined>(undefined);
  
  const handleSummaryUpdate = (s: EnsembleSummaryAPI | null, loc?: {lat: number, lon: number}, lt?: number) => {
    setSummary(s);
    setMapLocation(loc);
    setMapLeadTime(lt);
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans">
      
      {/* 1. Top Station Context Bar */}
      <div className="p-5 sm:p-6 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-ensemble/15 border border-ensemble/30 flex items-center justify-center text-ensemble shrink-0">
            <MapIcon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-black text-white tracking-tight">
                Geospatial Forecast Canvas
              </h1>
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-ensemble/10 text-ensemble text-[10px] font-mono font-semibold">
                <Sparkles className="w-3 h-3" /> LIVE NWP
              </span>
            </div>
            <span className="text-xs text-text-secondary font-mono">
              Target: <strong className="text-white font-medium">{location.name}</strong> [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]
            </span>
          </div>
        </div>

        {/* Quick Station Jumper */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-muted uppercase">Presets:</span>
          <div className="flex flex-wrap items-center gap-1.5">
            {presets.map((p) => {
              const isActive = p.name === location.name;
              return (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => setLocation(p)}
                  className={`px-3 py-1 rounded-lg transition-all text-xs font-mono ${
                    isActive 
                      ? "bg-ensemble text-slate-950 font-bold shadow-md" 
                      : "bg-background/80 border border-border-subtle text-text-secondary hover:text-white hover:border-ensemble/30"
                  }`}
                >
                  {p.name}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 2. Main Workstation Layout: Map Canvas + Forecast Decision Panel */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* Left: Interactive Map Canvas (7 cols on xl) */}
        <div className="xl:col-span-7 flex flex-col gap-2">
          <div className="rounded-2xl overflow-hidden border border-border-subtle shadow-2xl bg-panel/90 flex flex-col min-h-[620px]">
            <div className="py-2.5 px-4 border-b border-white/5 flex items-center justify-between bg-background/50 text-xs">
              <div className="flex items-center gap-2 font-bold text-white tracking-tight">
                <Compass className="w-4 h-4 text-ensemble" />
                <span>Spatial Map Workstation</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
                <Crosshair className="w-3 h-3 text-ensemble" />
                <span>Click map to sync coordinates</span>
              </div>
            </div>
            <div className="p-0 flex-1 overflow-hidden relative min-h-[580px]">
              <MapWrapper
                height="h-[580px]"
                showLayerSlots={true}
                initialOverlay="ensemble"
                onSummaryUpdate={handleSummaryUpdate}
              />
            </div>
          </div>
        </div>

        {/* Right: Scientific Forecast Decision Panel (5 cols on xl) */}
        <div className="xl:col-span-5 flex flex-col gap-2">
          <ForecastDecisionPanel
            summary={summary}
            loading={!summary}
            className="min-h-[620px] shadow-2xl"
            lat={mapLocation?.lat}
            lon={mapLocation?.lon}
            leadTime={mapLeadTime}
          />
        </div>
      </div>

      {/* 3. Architectural Layer Telemetry Disclosure (Progressive Disclosure) */}
      <div className="p-4 rounded-2xl bg-panel/85 backdrop-blur-md border border-border-subtle shadow-xl space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
          <div className="flex items-center gap-2 text-white font-bold">
            <Layers className="w-4 h-4 text-ensemble" />
            <span>NWP Grid Architecture &amp; Spatial Protocol</span>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            0.25° Mesh Resolution · Null-Safety Enforced
          </span>
        </div>

        <p className="text-xs text-text-secondary leading-snug">
          Overlays render discrete 0.25° (~28 km) NWP grid cells from ECMWF IFS, NOAA GFS, and ECMWF AIFS. The ensemble blends verified active models without zero substitution.
        </p>

        <details className="pt-1 group border-t border-white/5">
          <summary className="text-[11px] font-mono text-ensemble hover:text-white cursor-pointer select-none transition-colors">
            [View mathematical grid protocol &amp; spread definitions]
          </summary>
          <div className="mt-2 p-3 rounded-xl bg-background/50 border border-white/5 text-[11px] font-mono text-text-muted leading-relaxed space-y-1">
            <p>
              • Blended surface synthesizes cell values using inverse-error skill weights normalized exclusively across verified models.
            </p>
            <p>
              • Model Spread is defined as <code className="text-white">max(valid) − min(valid)</code>, directly reflecting pairwise difference <code className="text-white">|IFS − GFS|</code>.
            </p>
            <p>
              • AIFS missing responses never trigger zero substitution or synthetic spatial interpolation.
            </p>
          </div>
        </details>
      </div>
    </div>
  );
}
