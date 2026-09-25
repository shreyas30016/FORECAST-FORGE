"use client";

import { useState, useEffect } from "react";
import ReplayPanel from "@/components/replay/ReplayPanel";
import { api } from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import { useCopilot } from "@/context/CopilotContext";

export default function ReplayPage() {
  const { location } = useLocation();
  const { setCopilotContext } = useCopilot();
  const [customLat, setCustomLat] = useState<string | null>(null);
  const [customLon, setCustomLon] = useState<string | null>(null);

  const lat = customLat ?? (location?.latitude ? location.latitude.toFixed(4) : "19.0760");
  const lon = customLon ?? (location?.longitude ? location.longitude.toFixed(4) : "72.8777");
  const [run, setRun] = useState("2026-09-10T00:00");
  const [variable, setVariable] = useState("temperature_2m");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leadTime, setLeadTime] = useState(0);

  // Sync Copilot Context with active Replay snapshot
  useEffect(() => {
    const activeSnapshot = data?.snapshots?.find(
      (s: { forecast_time_decision?: { lead_time_hours?: number } }) =>
        s.forecast_time_decision?.lead_time_hours === leadTime
    );

    if (data && activeSnapshot) {
      setCopilotContext({
        page: "replay",
        location: location?.name || "Selected Location",
        latitude: parseFloat(lat),
        longitude: parseFloat(lon),
        variable,
        lead_time_hours: leadTime,
        valid_time: activeSnapshot.forecast_time_decision?.valid_time,
        run_time: data.run,
        trace_id: activeSnapshot.trace_id || null,
        replay_id: data.replay_id,
        replay_status: activeSnapshot.forecast_time_decision?.replay_integrity_status,
        provenance_status: activeSnapshot.forecast_time_decision?.data_quality_status,
        forecast_value: activeSnapshot.forecast_time_decision?.final_blended_value,
        realized_value: activeSnapshot.later_verification?.reference_value ?? null,
      });
    } else {
      setCopilotContext({
        page: "replay",
        location: location?.name || "Selected Location",
        latitude: parseFloat(lat),
        longitude: parseFloat(lon),
        variable,
        lead_time_hours: leadTime,
        run_time: run,
      });
    }
  }, [data, leadTime, lat, lon, variable, location?.name, run, setCopilotContext]);

  const fetchReplay = async () => {
    setLoading(true);
    setError(null);
    try {
      const json = await api.getReplayTimeline(run, lat, lon, variable);
      setData(json);
      setLeadTime(0); // Reset scrubber
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-7xl mx-auto space-y-6 pb-12 font-sans">
      {/* Header Bar */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-40 bg-ensemble/10 rounded-full blur-3xl pointer-events-none" />
        
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-ensemble animate-pulse" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-ensemble font-semibold">
              Causal Forecast Verification
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Forecast Decision Replay
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Strict causal replay of historical operational forecast cycles against later verified reality
          </p>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-wrap items-end gap-3 p-4 sm:p-5 bg-panel/85 backdrop-blur-md border border-border-subtle rounded-2xl shadow-xl">
        <div className="space-y-1">
          <label className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Exact Run (T0 UTC)</label>
          <input
            type="datetime-local"
            value={run}
            onChange={(e) => setRun(e.target.value)}
            className="px-3 py-2 bg-background/80 border border-white/10 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-ensemble/50"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Latitude</label>
          <input
            type="number"
            step="0.01"
            value={lat}
            onChange={(e) => setCustomLat(e.target.value)}
            className="w-24 px-3 py-2 bg-background/80 border border-white/10 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-ensemble/50"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Longitude</label>
          <input
            type="number"
            step="0.01"
            value={lon}
            onChange={(e) => setCustomLon(e.target.value)}
            className="w-24 px-3 py-2 bg-background/80 border border-white/10 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-ensemble/50"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Variable</label>
          <select
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
            className="px-3 py-2 bg-background/80 border border-white/10 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-ensemble/50"
          >
            <option value="temperature_2m">Temperature (2m)</option>
            <option value="precipitation">Precipitation</option>
            <option value="wind_speed_10m">Wind Speed (10m)</option>
          </select>
        </div>
        <button
          onClick={fetchReplay}
          disabled={loading}
          className="px-4 py-2 bg-ensemble text-slate-950 rounded-xl text-xs font-bold font-mono hover:bg-ensemble/90 transition-all shadow-md active:scale-95"
        >
          {loading ? "Replaying..." : "Start Replay"}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-status-unavailable/10 text-status-unavailable rounded-xl border border-status-unavailable/30 text-xs font-mono">
          {error}
        </div>
      )}

      {data && (
        <div className="space-y-6">
          {/* Scrubber */}
          <div className="bg-panel/85 backdrop-blur-md border border-border-subtle rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Lead-Time Scrubber
              </h2>
              <span className="text-xs font-mono text-ensemble font-bold">
                Selected: +{leadTime}h lead
              </span>
            </div>
            <div className="flex justify-between items-center relative py-2">
              <div className="absolute h-0.5 bg-white/10 w-full top-1/2 -translate-y-1/2 z-0" />
              {[0, 24, 48, 72, 96, 120, 144, 168].map((t) => {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const hasData = data.snapshots.some((s: any) => s.forecast_time_decision.lead_time_hours === t);
                return (
                  <button
                    key={t}
                    disabled={!hasData}
                    onClick={() => setLeadTime(t)}
                    className={`relative z-10 w-10 h-10 rounded-xl border transition-all flex items-center justify-center text-xs font-mono font-bold
                      ${
                        leadTime === t
                          ? "bg-ensemble border-ensemble text-slate-950 scale-110 shadow-lg shadow-ensemble/20"
                          : hasData
                          ? "bg-background/90 border-white/10 hover:border-ensemble text-white"
                          : "bg-background/40 border-white/5 text-text-muted opacity-40 cursor-not-allowed"
                      }
                    `}
                  >
                    +{t}h
                  </button>
                );
              })}
            </div>
          </div>

          <ReplayPanel 
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            snapshot={data.snapshots.find((s: any) => s.forecast_time_decision.lead_time_hours === leadTime)} 
          />
        </div>
      )}
    </main>
  );
}
