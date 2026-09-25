"use client";

import React, { useState } from "react";
import { 
  Clock, 
  ShieldAlert, 
  Target, 
  Info, 
  Activity,
  Eye
} from "lucide-react";
import { DecisionTraceDrawer } from "@/components/shared/DecisionTraceDrawer";
import { useSettings } from "@/context/SettingsContext";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function ReplayPanel({ snapshot }: { snapshot: any }) {
  const { convertTemp, convertTempDelta, tempSymbol } = useSettings();
  const [reveal, setReveal] = useState(false);
  const [isTraceOpen, setTraceOpen] = useState(false);

  if (!snapshot) {
    return (
      <div className="p-8 text-center text-text-muted border border-dashed border-white/10 rounded-2xl font-mono text-xs">
        Select a lead time from the scrubber to inspect the replay snapshot.
      </div>
    );
  }

  const decision = snapshot.forecast_time_decision;
  const verification = snapshot.later_verification;
  const isBust = verification?.realized_error > 2.0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start font-sans">
      {/* DECISION VIEW */}
      <div className="bg-panel/85 backdrop-blur-md border border-border-subtle rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-ensemble" />
            <h3 className="font-extrabold text-base text-white tracking-tight">Forecast-Time Decision</h3>
          </div>
          <button
            onClick={() => setTraceOpen(true)}
            className="px-3 py-1 bg-ensemble/10 text-ensemble text-[10px] font-bold rounded-lg border border-ensemble/30 hover:bg-ensemble/20 transition-colors uppercase font-mono tracking-wider"
          >
            Decision Trace
          </button>
        </div>

        <div className="bg-background/60 text-text-secondary text-xs px-3 py-2 rounded-xl font-mono flex items-center gap-2 border border-white/5">
          <Info className="w-3.5 h-3.5 text-ensemble shrink-0" />
          <span className="truncate">Causal isolation · Initialized {new Date(decision.initialization_time).toISOString().replace("T", " ").slice(0, 16)} UTC</span>
        </div>
        
        <DecisionTraceDrawer
          isOpen={isTraceOpen}
          onClose={() => setTraceOpen(false)}
          replayId={snapshot.replay_id}
        />

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-background/50 border border-white/5 rounded-xl p-3.5 space-y-1.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">Blended Forecast</span>
            <div className="text-3xl font-black text-white font-sans">
              {decision.final_blended_value ? `${convertTemp(decision.final_blended_value).toFixed(2)}${tempSymbol}` : "—"}
            </div>
            <div className="text-xs text-text-muted space-y-1 pt-1 font-mono">
              {Object.entries(decision.spatial_weights).map(([model, w]) => (
                <div key={model} className="flex justify-between text-[11px]">
                  <span className="truncate text-text-secondary">{model.replace("ecmwf_", "").replace("_seamless", "")}</span>
                  <span className="text-white font-bold">{((w as number) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-background/50 border border-white/5 rounded-xl p-3.5 space-y-1.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">Regime Engine</span>
            {decision.regime ? (
              <>
                <div className="text-2xl font-black text-white font-sans">Regime {decision.regime.regime_id}</div>
                <div className="text-[10px] font-mono text-text-muted truncate">
                  v{decision.regime.regime_model_version}
                </div>
              </>
            ) : (
              <div className="text-xs font-mono text-text-muted">Standard NWP</div>
            )}
          </div>
        </div>

        <div className="bg-background/50 border border-white/5 rounded-xl p-3.5 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Bust Risk Surveillance</span>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-md border ${
              decision.bust_signal.signal === 'ELEVATED' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' :
              decision.bust_signal.signal === 'NORMAL' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
              'bg-white/5 text-text-muted border-white/10'
            }`}>
              Bust: {decision.bust_signal.signal}
            </span>
          </div>
          
          <div className="space-y-1.5 font-mono text-xs">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {decision.extreme_guidance.map((ext: any, i: number) => (
              <div key={i} className="flex justify-between items-center text-xs py-1 border-t border-white/5 first:border-0 first:pt-0">
                <span className="capitalize text-text-secondary">{ext.event_type.replace(/_/g, ' ')} (&gt;{ext.threshold})</span>
                {ext.status === "AVAILABLE" ? (
                  <span className="text-white font-bold">{(ext.probability * 100).toFixed(1)}%</span>
                ) : (
                  <span className="text-[10px] text-text-muted">UNAVAILABLE</span>
                )}
              </div>
            ))}
          </div>

          {decision.probabilistic_status === "UNAVAILABLE" && (
            <div className="text-[11px] text-amber-400/90 bg-amber-500/10 p-2 rounded-lg flex items-center gap-1.5 border border-amber-500/20 font-mono">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              <span>Exact-run probabilistic provenance unavailable.</span>
            </div>
          )}
        </div>
      </div>

      {/* VERIFICATION VIEW */}
      <div className="bg-panel/85 backdrop-blur-md border border-border-subtle rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-sky-400" />
            <h3 className="font-extrabold text-base text-white tracking-tight">Realized Verification</h3>
          </div>
          {!reveal && (
            <button 
              onClick={() => setReveal(true)}
              className="flex items-center gap-1 text-xs px-3 py-1 bg-sky-500 text-slate-950 font-bold rounded-lg hover:bg-sky-400 transition font-mono"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Reveal Reality</span>
            </button>
          )}
        </div>

        {!reveal ? (
          <div className="h-64 border border-dashed border-white/10 rounded-xl flex flex-col items-center justify-center text-text-muted bg-background/30 gap-2">
            <Target className="w-8 h-8 opacity-40 text-sky-400" />
            <p className="font-bold text-xs text-white">Post-Event Reality Masked</p>
            <p className="text-[11px] font-mono text-text-muted">Click reveal to inspect verified ERA5 reanalysis reference benchmark.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-background/60 text-text-secondary text-xs px-3 py-2 rounded-xl font-mono flex items-center gap-2 border border-white/5">
              <Activity className="w-3.5 h-3.5 text-sky-400 shrink-0" />
              <span>ERA5 Benchmark valid: {new Date(verification.valid_time).toISOString().replace("T", " ").slice(0, 16)} UTC</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background/50 border border-white/5 rounded-xl p-3.5 space-y-1">
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">Realized Value</span>
                <div className="text-3xl font-black text-white font-sans">
                  {verification.reference_value ? `${convertTemp(verification.reference_value).toFixed(2)}${tempSymbol}` : "—"}
                </div>
                <span className="text-[10px] font-mono text-text-muted">ERA5 Reanalysis Reference</span>
              </div>
              
              <div className="bg-background/50 border border-white/5 rounded-xl p-3.5 space-y-1">
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">Realized Error</span>
                <div className={`text-3xl font-black font-sans ${isBust ? "text-rose-400" : "text-emerald-400"}`}>
                  {verification.realized_error ? `${convertTempDelta(verification.realized_error).toFixed(2)}${tempSymbol}` : "—"}
                </div>
                <span className="text-[10px] font-mono text-text-muted">|Forecast − ERA5 Ref|</span>
              </div>
            </div>

            {/* Post-Mortem Card */}
            <div className="p-3.5 bg-background/50 border border-white/5 rounded-xl space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-white font-bold text-[11px] uppercase tracking-wide">Verification Outcome</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  isBust ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                }`}>
                  {isBust ? "HIGH ERROR / BUST" : "LOW ERROR / VERIFIED"}
                </span>
              </div>
              <p className="text-text-secondary text-xs font-sans leading-relaxed">
                Absolute error was {verification.realized_error ? `${convertTempDelta(verification.realized_error).toFixed(2)}${tempSymbol}` : "unknown"}.
                {isBust 
                  ? " Model divergence preceded significant deviation." 
                  : " Multi-model consensus successfully captured the atmospheric state."}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
