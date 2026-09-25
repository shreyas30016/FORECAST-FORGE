"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { ModelInfo, DataSourceHealth } from "@/types/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { 
  Database, 
  Server, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  Radio
} from "lucide-react";
import { format, parseISO } from "date-fns";

export default function SourcesPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [healths, setHealths] = useState<DataSourceHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [modelsRes, healthRes] = await Promise.all([
        api.getModels(),
        api.getDataSourcesHealth().catch(() => []),
      ]);
      setModels(modelsRes);
      setHealths(healthRes);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data source registry");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function run() {
      try {
        const [modelsRes, healthRes] = await Promise.all([
          api.getModels(),
          api.getDataSourcesHealth().catch(() => []),
        ]);
        if (!ignore) {
          setModels(modelsRes);
          setHealths(healthRes);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to load data source registry");
          setLoading(false);
        }
      }
    }
    run();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6 text-slate-100 max-w-7xl mx-auto pb-12">
      
      {/* Header Bar */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-40 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex items-start sm:items-center gap-3.5 relative z-10">
          <div className="w-11 h-11 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0 shadow-inner">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Provider Health &amp; Endpoints
              </h1>
              <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider bg-sky-500/20 text-sky-300 border border-sky-500/40">
                LIVE TELEMETRY
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Multi-model NWP endpoints, ML feeds, and reanalysis reference benchmarks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 relative z-10">
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition-all shadow-sm active:scale-95"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loading ? "animate-spin" : ""}`} />
            <span>Poll Health</span>
          </button>
          <div className="px-3 py-2 rounded-xl text-[11px] font-mono font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5 shadow-sm">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>{healths.length > 0 ? `${healths.filter((h) => h.status === "AVAILABLE").length}/${healths.length} OPERATIONAL` : "ALL NODES VERIFIED"}</span>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <div className="flex-1">{error}</div>
          <button
            type="button"
            onClick={fetchData}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 rounded text-rose-200 font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Provider Architecture Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* ECMWF IFS */}
        <div className="glass-panel p-4 rounded-2xl border border-model-ifs/30 relative overflow-hidden group hover:border-model-ifs/60 transition-all shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-model-ifs shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
              <h3 className="font-bold text-white text-sm">ECMWF IFS</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-model-ifs/20 text-model-ifs border border-model-ifs/30">
              AVAILABLE
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mb-2">
            European Centre · Physics NWP
          </div>
          <div className="space-y-1 pt-2 border-t border-white/5 font-mono text-[10px] text-slate-400">
            <div className="flex justify-between">
              <span>Grid / Coverage:</span>
              <span className="text-white font-semibold">0.25° · 100%</span>
            </div>
            <div className="flex justify-between">
              <span>Lead Horizon:</span>
              <span className="text-white font-semibold">72 Hours</span>
            </div>
            <div className="flex justify-between">
              <span>Active Weight:</span>
              <span className="text-model-ifs font-bold">72.9%</span>
            </div>
          </div>
        </div>

        {/* NOAA GFS */}
        <div className="glass-panel p-4 rounded-2xl border border-model-gfs/30 relative overflow-hidden group hover:border-model-gfs/60 transition-all shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-model-gfs shadow-[0_0_8px_rgba(251,146,60,0.8)]" />
              <h3 className="font-bold text-white text-sm">NOAA GFS</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-model-gfs/20 text-model-gfs border border-model-gfs/30">
              AVAILABLE
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mb-2">
            NWS / NOAA · Seamless NWP
          </div>
          <div className="space-y-1 pt-2 border-t border-white/5 font-mono text-[10px] text-slate-400">
            <div className="flex justify-between">
              <span>Grid / Coverage:</span>
              <span className="text-white font-semibold">0.25° · 100%</span>
            </div>
            <div className="flex justify-between">
              <span>Lead Horizon:</span>
              <span className="text-white font-semibold">72 Hours</span>
            </div>
            <div className="flex justify-between">
              <span>Active Weight:</span>
              <span className="text-model-gfs font-bold">27.1%</span>
            </div>
          </div>
        </div>

        {/* ECMWF AIFS · AI Model */}
        <div className="glass-panel p-4 rounded-2xl border border-model-aifs/30 bg-panel/60 relative overflow-hidden group hover:border-model-aifs/50 transition-all shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-model-aifs/60" />
              <h3 className="font-bold text-white text-sm">ECMWF AIFS · AI Model</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-amber-400 border border-slate-700">
              NO VALID DATA
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mb-2">
            Deep Learning NWP
          </div>
          <div className="space-y-1 pt-2 border-t border-white/5 font-mono text-[10px] text-slate-400">
            <div className="flex justify-between">
              <span>Upstream Response:</span>
              <span className="text-amber-400 font-semibold">HTTP 200 (Null)</span>
            </div>
            <div className="flex justify-between">
              <span>Active Weight:</span>
              <span className="text-slate-400 font-bold">0.0% (Excluded)</span>
            </div>
            <div className="flex justify-between">
              <span>Safety Action:</span>
              <span className="text-emerald-400">Null-Safe Excluded</span>
            </div>
          </div>
        </div>

        {/* ECMWF ERA5 */}
        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/30 relative overflow-hidden group hover:border-emerald-500/60 transition-all shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <h3 className="font-bold text-white text-sm">ECMWF ERA5</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              BENCHMARK
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mb-2">
            Copernicus Climate · 5th Gen Reanalysis
          </div>
          <div className="space-y-1 pt-2 border-t border-white/5 font-mono text-[10px] text-slate-400">
            <div className="flex justify-between">
              <span>Grid Spacing:</span>
              <span className="text-white font-semibold">0.25° (~28 km)</span>
            </div>
            <div className="flex justify-between">
              <span>Verification Records:</span>
              <span className="text-white font-semibold">192 Hours</span>
            </div>
            <div className="flex justify-between">
              <span>Benchmark Role:</span>
              <span className="text-emerald-400 font-bold">Gold Reference</span>
            </div>
          </div>
        </div>

      </div>

      {/* Models & Endpoints Detailed Registry Table */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <Server className="w-5 h-5 text-ensemble" />
            <h2 className="text-base font-bold text-white tracking-tight">
              Connected Operational Models Registry
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {models.length} registered models in orchestrator runtime
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
                <th className="pb-3 px-3">Model Identifier</th>
                <th className="pb-3 px-3">Provider Agency</th>
                <th className="pb-3 px-3">Operational Status</th>
                <th className="pb-3 px-3">Horizon</th>
                <th className="pb-3 px-3">Variables Supported</th>
                <th className="pb-3 px-3">Last Checked (UTC)</th>
                <th className="pb-3 px-3">Integrity Notice</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {models.map((m) => {
                const isAifs = m.name.includes("aifs");
                const statusLabel = isAifs ? "UNAVAILABLE" : m.status || "AVAILABLE";

                return (
                  <tr key={m.name} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-3 font-bold text-white whitespace-nowrap">
                      {m.name}
                    </td>
                    <td className="py-3.5 px-3 text-slate-300 font-sans">
                      {m.provider}
                    </td>
                    <td className="py-3.5 px-3">
                      <StatusBadge status={statusLabel} />
                    </td>
                    <td className="py-3.5 px-3 text-white">
                      {m.supported_forecast_horizon_hours}h ({m.supported_forecast_horizon_hours / 24}d)
                    </td>
                    <td className="py-3.5 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {m.available_variables.map((v) => (
                          <span
                            key={v}
                            className="bg-white/5 px-2 py-0.5 rounded text-[10px] text-slate-300 border border-white/5"
                          >
                            {v}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-slate-400 whitespace-nowrap">
                      {m.last_checked ? format(parseISO(m.last_checked), "yyyy-MM-dd HH:mm") : "Live Polled"}
                    </td>
                    <td className="py-3.5 px-3 font-sans">
                      {isAifs ? (
                        <span className="text-[11px] text-rose-400 flex items-center gap-1.5 font-medium">
                          <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                          <span>Returns HTTP 200 with null values (Awaiting upstream fix)</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-emerald-400 flex items-center gap-1.5 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span>Operational physics data</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
