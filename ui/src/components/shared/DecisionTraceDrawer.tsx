"use client";

import React, { useState, useEffect } from "react";
import { X, ShieldAlert, Cpu, ChevronDown, ChevronRight, Activity, Clock, ShieldCheck, HelpCircle } from "lucide-react";
import { api } from "@/lib/api";

interface DecisionTraceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  lat?: number;
  lon?: number;
  validTime?: string;
  leadTime?: number;
  variable?: string;
  traceId?: string;
  replayId?: string;
}

const CollapsibleSection = ({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border-subtle rounded-lg overflow-hidden bg-background/30 mb-3">
      <button 
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center justify-between bg-panel/50 hover:bg-panel/80 transition-colors text-left"
      >
        <span className="font-bold text-xs uppercase tracking-wider text-text-secondary">{title}</span>
        {open ? <ChevronDown className="w-4 h-4 text-text-muted" /> : <ChevronRight className="w-4 h-4 text-text-muted" />}
      </button>
      {open && (
        <div className="p-4 border-t border-border-subtle text-xs space-y-3">
          {children}
        </div>
      )}
    </div>
  );
};

export function DecisionTraceDrawer({
  isOpen,
  onClose,
  lat = 0,
  lon = 0,
  validTime = "",
  leadTime = 0,
  variable = "temperature_2m",
  traceId,
  replayId
}: DecisionTraceDrawerProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [trace, setTrace] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isOpen) {
      if (!traceId && !replayId && (!lat || !lon || !validTime)) {
        return;
      }
      // eslint-disable-next-line
      setLoading(true);
      setError("");
      api.getDecisionTrace(lat, lon, validTime, leadTime, variable, traceId, replayId)
        .then(data => {
          setTrace(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message || "Failed to load trace");
          setLoading(false);
        });
    }
  }, [isOpen, lat, lon, validTime, leadTime, variable, traceId, replayId]);

  if (!isOpen) return null;

  const renderIntegrityBadge = (status: string) => {
    switch(status) {
      case "EXACT":
        return <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 rounded-md font-mono text-[10px] font-bold flex items-center gap-1"><ShieldCheck className="w-3 h-3"/> EXACT</span>;
      case "DEGRADED":
        return <span className="px-2 py-1 bg-amber-500/10 text-amber-500 border border-amber-500/30 rounded-md font-mono text-[10px] font-bold flex items-center gap-1"><ShieldAlert className="w-3 h-3"/> DEGRADED</span>;
      default:
        return <span className="px-2 py-1 bg-red-500/10 text-red-500 border border-red-500/30 rounded-md font-mono text-[10px] font-bold flex items-center gap-1"><HelpCircle className="w-3 h-3"/> UNAVAILABLE</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md h-full bg-[#0a0a0c] border-l border-white/10 shadow-2xl flex flex-col font-sans overflow-hidden animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-black text-sm text-white uppercase tracking-wider">Decision Trace</h2>
              <div className="text-[10px] font-mono text-text-muted mt-0.5">Scientific Provenance Evidence</div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors text-text-muted hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-40 space-y-4 text-text-muted font-mono text-xs animate-pulse">
              <Activity className="w-6 h-6" />
              <p>Retrieving immutable trace evidence...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs font-mono">
              {error}
            </div>
          ) : trace ? (
            <div className="space-y-6">
              
              {/* Top Meta */}
              <div className="flex items-center justify-between bg-panel/50 p-3 rounded-lg border border-border-subtle">
                <span className="font-mono text-xs text-text-secondary">Integrity Status</span>
                {renderIntegrityBadge(trace.decision_integrity)}
              </div>

              {/* Context */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 bg-panel/30 border border-border-subtle rounded-lg">
                  <div className="text-[10px] uppercase text-text-muted font-bold mb-1">Forecast</div>
                  <div className="font-mono text-sm text-white font-bold">{trace.forecast?.value?.toFixed(2) || "—"} {trace.forecast?.unit}</div>
                </div>
                <div className="p-3 bg-panel/30 border border-border-subtle rounded-lg">
                  <div className="text-[10px] uppercase text-text-muted font-bold mb-1">Location</div>
                  <div className="font-mono text-sm text-white">{trace.context?.latitude?.toFixed(4)}, {trace.context?.longitude?.toFixed(4)}</div>
                </div>
                <div className="p-3 bg-panel/30 border border-border-subtle rounded-lg col-span-2 flex justify-between items-center">
                  <div>
                    <div className="text-[10px] uppercase text-text-muted font-bold mb-1">Valid Time</div>
                    <div className="font-mono text-xs text-blue-400 flex items-center gap-1"><Clock className="w-3 h-3"/> {trace.context?.valid_time}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] uppercase text-text-muted font-bold mb-1">Lead Time</div>
                    <div className="font-mono text-xs text-white">+{trace.context?.lead_time_hours}h</div>
                  </div>
                </div>
              </div>

              {/* Weights Evidence */}
              <CollapsibleSection title="Weights Evidence" defaultOpen={true}>
                {trace.weights_evidence && trace.weights_evidence.length > 0 ? (
                  <div className="space-y-4">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {trace.weights_evidence.map((we: any, i: number) => (
                      <div key={i} className="border border-white/5 bg-background/50 rounded p-3">
                        <div className="flex justify-between items-center border-b border-white/5 pb-2 mb-2">
                          <span className="font-bold text-white">{we.model}</span>
                          <span className="font-mono text-ensemble font-bold">{(we.weight * 100).toFixed(1)}%</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-text-muted">
                          <div>RMSE: <span className="text-white">{we.rmse !== null ? we.rmse.toFixed(3) : 'N/A'}</span></div>
                          <div>MAE: <span className="text-white">{we.mae !== null ? we.mae.toFixed(3) : 'N/A'}</span></div>
                          <div>Bias: <span className="text-white">{we.bias !== null ? we.bias.toFixed(3) : 'N/A'}</span></div>
                          <div>Samples: <span className="text-white">{we.sample_count}</span></div>
                        </div>
                        <div className="mt-2 pt-2 border-t border-white/5 text-[10px] text-text-secondary leading-relaxed">
                          <span className="font-bold text-text-muted">WHY THIS WEIGHT?</span><br/>
                          Calculated using {we.methodology} methodology over a historical evaluation period. 
                          Reference benchmark: ERA5 reanalysis. Spatial proximity weighting applied.
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-amber-500 font-mono">No weight evidence available.</div>
                )}
              </CollapsibleSection>

              {/* Weather Regime */}
              <CollapsibleSection title="Weather Regime" defaultOpen={true}>
                {trace.regime ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-text-muted">Regime ID</span>
                      <span className="font-mono font-bold text-white text-lg">{trace.regime.regime_id}</span>
                    </div>
                    <div className="flex justify-between items-center border-t border-white/5 pt-2">
                      <span className="text-text-muted">Model Version</span>
                      <span className="font-mono text-white">{trace.regime.model_version}</span>
                    </div>
                    {trace.regime.model_hash && (
                      <div className="flex justify-between items-center border-t border-white/5 pt-2">
                        <span className="text-text-muted">Artifact Hash</span>
                        <span className="font-mono text-[9px] text-blue-400 break-all w-32 text-right">{trace.regime.model_hash}</span>
                      </div>
                    )}
                    <div className="mt-2 pt-2 border-t border-white/5 text-[10px] text-text-secondary leading-relaxed">
                      <span className="font-bold text-text-muted">WHY THIS REGIME?</span><br/>
                      Inferred via clustering (e.g. KMeans) on dynamic atmospheric state predictors at T0.
                    </div>
                  </div>
                ) : (
                  <div className="text-amber-500 font-mono flex gap-2">
                     <ShieldAlert className="w-3 h-3 mt-0.5" />
                     <span>
                        <span className="font-bold block mb-1">WHY UNAVAILABLE?</span>
                        Temporal provenance lockout. The requested historical snapshot occurred before the regime artifact&apos;s valid evaluation date.
                     </span>
                  </div>
                )}
              </CollapsibleSection>

              {/* Extreme Guidance */}
              <CollapsibleSection title="Extreme Guidance">
                {trace.extremes && trace.extremes.length > 0 ? (
                  <div className="space-y-3">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {trace.extremes.map((ex: any, i: number) => (
                      <div key={i} className="flex justify-between items-center border-b border-white/5 pb-2 last:border-0 last:pb-0">
                        <div>
                          <div className="font-bold capitalize text-white">{ex.event_type.replace(/_/g, ' ')}</div>
                          <div className="font-mono text-[9px] text-text-muted">Thresh: {ex.threshold} {trace.forecast?.unit}</div>
                        </div>
                        {ex.status === "AVAILABLE" ? (
                          <div className="text-right">
                            <div className="font-mono text-amber-500 font-bold">{(ex.probability * 100).toFixed(1)}%</div>
                            <div className="font-mono text-[9px] text-text-muted">{ex.valid_members}/{ex.total_members} members</div>
                          </div>
                        ) : (
                          <span className="text-[10px] font-mono text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded">UNAVAILABLE</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-amber-500 font-mono flex gap-2">
                    <ShieldAlert className="w-3 h-3 mt-0.5 shrink-0" />
                    <span>
                      <span className="font-bold block mb-1">WHY UNAVAILABLE?</span>
                      Probabilistic historical run identity could not be deterministically verified.
                    </span>
                  </div>
                )}
              </CollapsibleSection>

              {/* Forecast Bust */}
              <CollapsibleSection title="Forecast Bust">
                {trace.bust ? (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-text-muted">Signal</span>
                      <span className={`px-2 py-1 font-mono text-[10px] font-bold rounded border ${
                        trace.bust.signal === 'ELEVATED' ? 'bg-red-500/10 text-red-500 border-red-500/30' :
                        trace.bust.signal === 'NORMAL' ? 'bg-green-500/10 text-green-500 border-green-500/30' :
                        'bg-gray-500/10 text-gray-500 border-gray-500/30'
                      }`}>
                        {trace.bust.signal}
                      </span>
                    </div>
                    {trace.bust.status === "AVAILABLE" ? (
                      <>
                        <div className="flex justify-between items-center border-t border-white/5 pt-2">
                          <span className="text-text-muted">Threshold</span>
                          <span className="font-mono text-white">{trace.bust.threshold || "N/A"}</span>
                        </div>
                        <div className="flex justify-between items-center border-t border-white/5 pt-2">
                          <span className="text-text-muted">Model Version</span>
                          <span className="font-mono text-white">{trace.bust.model_version || "N/A"}</span>
                        </div>
                        {trace.bust.model_hash && (
                          <div className="flex justify-between items-center border-t border-white/5 pt-2">
                            <span className="text-text-muted">Hash</span>
                            <span className="font-mono text-[9px] text-blue-400 break-all w-32 text-right">{trace.bust.model_hash}</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="mt-2 text-amber-500 font-mono flex gap-2 text-[10px]">
                        <ShieldAlert className="w-3 h-3 mt-0.5 shrink-0" />
                        <span>Temporal provenance lockout. Bust model version invalid for this snapshot.</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-amber-500 font-mono text-[10px]">No bust trace.</div>
                )}
              </CollapsibleSection>

              {/* Provenance */}
              <CollapsibleSection title="Trace Metadata">
                <div className="space-y-2 text-[10px] font-mono text-text-muted">
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span>Trace ID</span>
                    <span className="text-white truncate max-w-[150px]">{trace.trace_id}</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span>Generated</span>
                    <span className="text-white">{trace.created_at}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Forecast Source</span>
                    <span className="text-blue-400">{trace.forecast?.source || "API"}</span>
                  </div>
                </div>
              </CollapsibleSection>

            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 space-y-2 text-text-muted font-mono text-xs">
              <ShieldAlert className="w-6 h-6 text-amber-500/50" />
              <p>No trace evidence found.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
