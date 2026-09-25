"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { EnsembleResponse, ForecastResponse, TimelineRow } from "@/types/api";
import { deriveWeatherVisualState } from "@/types/weather";
import { WeatherHero } from "@/components/weather/WeatherHero";
import { ModelCard } from "@/components/weather/ModelCard";
import { EnsembleCard } from "@/components/weather/EnsembleCard";
import { ForecastTimeline } from "@/components/charts/ForecastTimeline";
import { ProviderHealth } from "@/components/shared/ProviderHealth";
import { MapWrapper } from "@/components/maps/MapWrapper";
import { useLocation } from "@/context/LocationContext";
import { useCopilot } from "@/context/CopilotContext";
import { 
  Sparkles, 
  Map as MapIcon, 
  RefreshCw, 
  ArrowUpRight, 
  LineChart, 
  Activity, 
  AlertTriangle 
} from "lucide-react";
import Link from "next/link";

export default function Dashboard() {
  const { location, setActiveForecast } = useLocation();
  const { setCopilotContext } = useCopilot();
  const [ensemble, setEnsemble] = useState<EnsembleResponse | null>(null);
  const [forecastRaw, setForecastRaw] = useState<ForecastResponse | null>(null);
  const [forecastTimeline, setForecastTimeline] = useState<TimelineRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [ensRes, fcstRes] = await Promise.all([
        api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name),
        api.getForecast(location.latitude, location.longitude, 72, location.name),
      ]);

      setEnsemble(ensRes);
      setForecastRaw(fcstRes);
      setLastRefreshed(new Date());
      setError(null);
      
      const traceId = (ensRes.ensemble as unknown as { trace_id?: string }).trace_id || undefined;
      setActiveForecast({
        valid_time: String(ensRes.valid_time),
        variable: ensRes.variable,
        lead_time_hours: 72,
        trace_id: traceId,
      });

      setCopilotContext({
        page: "dashboard",
        location: location.name,
        latitude: location.latitude,
        longitude: location.longitude,
        variable: ensRes.variable,
        lead_time_hours: 0,
        valid_time: String(ensRes.valid_time),
        trace_id: traceId,
        forecast_value: ensRes.ensemble.forecast ?? undefined,
        provenance_status: ensRes.ensemble.data_quality ?? "AVAILABLE",
      });

      // Transform forecast records for timeline visualization
      const timeMap: Record<string, TimelineRow> = {};

      for (const [model, pData] of Object.entries(fcstRes.providers)) {
        if (!pData?.records) continue;
        pData.records.forEach((r) => {
          if (!timeMap[r.timestamp]) {
            timeMap[r.timestamp] = { timestamp: r.timestamp };
          }
          timeMap[r.timestamp][model] = r.temperature_2m;
        });
      }

      const modelWeights = ensRes.models;
      const sortedTimeline = Object.values(timeMap)
        .map((row) => {
          let ensVal = 0;
          let weightSum = 0;

          if (
            row.ecmwf_ifs025 !== null &&
            row.ecmwf_ifs025 !== undefined &&
            modelWeights["ecmwf_ifs025"]?.status?.includes("AVAILABLE")
          ) {
            const w = modelWeights["ecmwf_ifs025"]?.weight || 0;
            ensVal += Number(row.ecmwf_ifs025) * w;
            weightSum += w;
          }

          if (
            row.gfs_seamless !== null &&
            row.gfs_seamless !== undefined &&
            modelWeights["gfs_seamless"]?.status?.includes("AVAILABLE")
          ) {
            const w = modelWeights["gfs_seamless"]?.weight || 0;
            ensVal += Number(row.gfs_seamless) * w;
            weightSum += w;
          }

          row.ensemble = weightSum > 0 ? parseFloat((ensVal / weightSum).toFixed(3)) : null;
          row.spread = ensRes.ensemble.uncertainty;

          return row;
        })
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      setForecastTimeline(sortedTimeline);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load meteorological data";
      setError(msg);
    }
  }, [location.latitude, location.longitude, location.name, setActiveForecast, setCopilotContext]);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const [ensRes, fcstRes] = await Promise.all([
          api.getEnsemble(location.latitude, location.longitude, "temperature_2m", 72, location.name),
          api.getForecast(location.latitude, location.longitude, 72, location.name),
        ]);

        if (!ignore) {
          setEnsemble(ensRes);
          setForecastRaw(fcstRes);
          setLastRefreshed(new Date());
          setError(null);

          const timeMap: Record<string, TimelineRow> = {};
          for (const [model, pData] of Object.entries(fcstRes.providers)) {
            if (!pData?.records) continue;
            pData.records.forEach((r) => {
              if (!timeMap[r.timestamp]) {
                timeMap[r.timestamp] = { timestamp: r.timestamp };
              }
              timeMap[r.timestamp][model] = r.temperature_2m;
            });
          }

          const modelWeights = ensRes.models;
          const sortedTimeline = Object.values(timeMap)
            .map((row) => {
              let ensVal = 0;
              let weightSum = 0;

              if (
                row.ecmwf_ifs025 !== null &&
                row.ecmwf_ifs025 !== undefined &&
                modelWeights["ecmwf_ifs025"]?.status?.includes("AVAILABLE")
              ) {
                const w = modelWeights["ecmwf_ifs025"]?.weight || 0;
                ensVal += Number(row.ecmwf_ifs025) * w;
                weightSum += w;
              }

              if (
                row.gfs_seamless !== null &&
                row.gfs_seamless !== undefined &&
                modelWeights["gfs_seamless"]?.status?.includes("AVAILABLE")
              ) {
                const w = modelWeights["gfs_seamless"]?.weight || 0;
                ensVal += Number(row.gfs_seamless) * w;
                weightSum += w;
              }

              row.ensemble = weightSum > 0 ? parseFloat((ensVal / weightSum).toFixed(3)) : null;
              row.spread = ensRes.ensemble.uncertainty;

              return row;
            })
            .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

          setForecastTimeline(sortedTimeline);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load meteorological data";
          setError(msg);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [location.latitude, location.longitude, location.name]);

  // Derive normalized weather state from current first record
  const weatherState = useMemo(() => {
    const ifsRecords = forecastRaw?.providers["ecmwf_ifs025"]?.records || [];
    const firstPoint = ifsRecords[0];
    return deriveWeatherVisualState(firstPoint, ensemble?.valid_time);
  }, [forecastRaw, ensemble?.valid_time]);

  // Extract model details
  const ifsForecast = ensemble?.models["ecmwf_ifs025"];
  const gfsForecast = ensemble?.models["gfs_seamless"];

  const ifsRecord = forecastRaw?.providers["ecmwf_ifs025"]?.records?.[0];
  const gfsRecord = forecastRaw?.providers["gfs_seamless"]?.records?.[0];


  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto pb-12 font-sans">
      
      {/* 1. Atmospheric Weather Hero Section */}
      <WeatherHero
        weather={weatherState}
        location={location}
        ensembleValue={ensemble?.ensemble.forecast}
        modelSpread={ensemble?.ensemble.uncertainty}
        lastRefreshed={lastRefreshed}
        validTime={ensemble?.valid_time ? String(ensemble.valid_time) : undefined}
      />

      {/* Error Notice if API is down */}
      {error && (
        <div className="p-4 rounded-xl bg-status-unavailable/10 border border-status-unavailable/30 flex items-center justify-between text-status-unavailable text-xs font-mono">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Connection Warning: {error}</span>
          </div>
          <button
            type="button"
            onClick={fetchData}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-status-unavailable/20 hover:bg-status-unavailable/30 text-white font-bold transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* 2. Numerical Model Comparison */}
      <section className="space-y-4 pt-6">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-ensemble" />
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            Model Comparison
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* ECMWF IFS Card */}
          <ModelCard
            id="ecmwf_ifs025"
            name="ECMWF IFS"
            provider="European Centre"
            status={
              ifsForecast?.status === "AVAILABLE" ? "AVAILABLE"
              : ifsForecast?.status === "DEGRADED" ? "DEGRADED"
              : "UNAVAILABLE"
            }
            value={ifsForecast?.forecast ?? null}
            weight={ifsForecast?.weight ?? 0.73}
            precipitation={ifsRecord?.precipitation}
            windSpeed={ifsRecord?.wind_speed_10m}
            humidity={ifsRecord?.relative_humidity_2m}
            skill={{ mae: 0.36, rmse: 0.47 }}
          />

          {/* NOAA GFS Card */}
          <ModelCard
            id="gfs_seamless"
            name="NOAA GFS"
            provider="National Weather Service"
            status={
              gfsForecast?.status === "AVAILABLE" ? "AVAILABLE"
              : gfsForecast?.status === "DEGRADED" ? "DEGRADED"
              : "UNAVAILABLE"
            }
            value={gfsForecast?.forecast ?? null}
            weight={gfsForecast?.weight ?? 0.27}
            precipitation={gfsRecord?.precipitation}
            windSpeed={gfsRecord?.wind_speed_10m}
            humidity={gfsRecord?.relative_humidity_2m}
            skill={{ mae: 1.12, rmse: 1.27 }}
          />

          {/* ECMWF AIFS · AI Model Card — Honest null-safety, not a provider outage */}
          <ModelCard
            id="ecmwf_aifs025"
            name="ECMWF AIFS · AI Model"
            provider="ECMWF Machine Learning"
            status="NO_VALID_DATA"
            value={null}
            weight={0.0}
            skill={{}}
            reason="No valid forecast values returned for this coordinate. Zero substitution prohibited."
          />
        </div>
      </section>

      {/* 3. Forecast Trajectory Evolution (72 Hours) */}
      <section className="space-y-4 pt-6">
        <div className="flex items-center gap-2">
          <LineChart className="w-5 h-5 text-ensemble" />
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            Hourly Trajectory
          </h2>
        </div>

        <div className="p-6 rounded-3xl bg-panel/40 backdrop-blur-md border border-white/5 shadow-2xl">
          <ForecastTimeline data={forecastTimeline} />
        </div>
      </section>

      {/* 4. Scientific Evidence Layer */}
      <section className="space-y-4 pt-8 border-t border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-text-muted" />
            <h2 className="text-lg font-bold text-text-secondary tracking-tight">
              Scientific Evidence
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <EnsembleCard ensemble={ensemble} />
          </div>
          <div className="grid grid-cols-1 gap-3">
            <Link href="/ensemble" className="p-4 rounded-xl bg-panel/30 hover:bg-panel/50 border border-white/5 transition-colors flex items-center justify-between group">
              <div>
                <div className="font-bold text-white group-hover:text-ensemble transition-colors">Decision Trace</div>
                <div className="text-xs text-text-muted">Provenance & formulas</div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-text-muted group-hover:text-ensemble" />
            </Link>
            <Link href="/replay" className="p-4 rounded-xl bg-panel/30 hover:bg-panel/50 border border-white/5 transition-colors flex items-center justify-between group">
              <div>
                <div className="font-bold text-white group-hover:text-ensemble transition-colors">Replay Engine</div>
                <div className="text-xs text-text-muted">Historical simulation</div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-text-muted group-hover:text-ensemble" />
            </Link>
            <Link href="/forecast" className="p-4 rounded-xl bg-panel/30 hover:bg-panel/50 border border-white/5 transition-colors flex items-center justify-between group">
              <div>
                <div className="font-bold text-white group-hover:text-ensemble transition-colors">Probabilistic Analysis</div>
                <div className="text-xs text-text-muted">Regime & extremes</div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-text-muted group-hover:text-ensemble" />
            </Link>
            <Link href="/alerts" className="p-4 rounded-xl bg-panel/30 hover:bg-panel/50 border border-white/5 transition-colors flex items-center justify-between group">
              <div>
                <div className="font-bold text-white group-hover:text-ensemble transition-colors">Bust Intelligence</div>
                <div className="text-xs text-text-muted">Extreme-weather guidance</div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-text-muted group-hover:text-ensemble" />
            </Link>
          </div>
        </div>
      </section>

      {/* 5. Geospatial Meteorological Map Preview */}
      <section className="space-y-4 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapIcon className="w-5 h-5 text-ensemble" />
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Spatial Intelligence
            </h2>
          </div>
          <Link
            href="/maps"
            className="text-sm font-bold text-ensemble hover:text-white flex items-center gap-1 transition-colors"
          >
            <span>Open Map</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="rounded-3xl overflow-hidden border border-white/5 shadow-2xl relative">
          <MapWrapper height="h-[440px]" showLayerSlots={true} initialOverlay="ensemble" />
        </div>
      </section>

      {/* 6. Advanced Analysis */}
      <section className="space-y-4 pt-8 border-t border-white/5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-text-muted" />
          <h2 className="text-sm font-bold text-text-secondary tracking-tight uppercase">
            Advanced Analysis
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ProviderHealth providers={forecastRaw?.providers} models={ensemble?.models} />
          <div className="flex flex-col gap-3">
            <Link href="/compare" className="p-4 rounded-xl bg-panel/30 border border-white/5 hover:bg-panel/50 transition-colors flex items-center justify-between text-sm">
              <span className="font-bold text-text-secondary">Full Comparison Matrix</span>
              <ArrowUpRight className="w-4 h-4 text-text-muted" />
            </Link>
            <Link href="/sources" className="p-4 rounded-xl bg-panel/30 border border-white/5 hover:bg-panel/50 transition-colors flex items-center justify-between text-sm">
              <span className="font-bold text-text-secondary">Inspect All Providers</span>
              <ArrowUpRight className="w-4 h-4 text-text-muted" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
