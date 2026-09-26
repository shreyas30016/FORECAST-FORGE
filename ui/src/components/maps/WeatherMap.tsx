"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Circle,
  Rectangle,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import { useLocation } from "@/context/LocationContext";
import { useSettings } from "@/context/SettingsContext";
import { api } from "@/lib/api";
import { GridResponse, GridCellAPI, EnsembleSummaryAPI, SpatialWeightGridResponse, SpatialLeadTimeWeightGridResponse, RegimeDefinition } from "@/types/api";
import {
  Crosshair,
  Layers,
  Thermometer,
  CloudRain,
  Wind as WindIcon,
  GitCompare,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Info,
  Cloud,
  Zap,
} from "lucide-react";
import CloudCoverLayer from "./CloudCoverLayer";
import WindFlowLayer from "./WindFlowLayer";
import PrecipitationLayer from "./PrecipitationLayer";
import { ProbabilisticPanel } from "../forecast/ProbabilisticPanel";
import { ExtremesPanel } from "../forecast/ExtremesPanel";
import { ForecastBustPanel } from "../forecast/ForecastBustPanel";

type OverlayType = "ensemble" | "temperature" | "precipitation" | "wind" | "cloud_cover" | "disagreement" | "uncertainty" | "weights" | "none";

interface WeatherMapProps {
  className?: string;
  height?: string;
  showLayerSlots?: boolean;
  initialOverlay?: OverlayType;
  onSummaryUpdate?: (summary: EnsembleSummaryAPI | null, location?: {lat: number, lon: number}, leadTime?: number) => void;
}

// Custom station reticle marker icon
function getCrosshairIcon() {
  return L.divIcon({
    className: "custom-station-pin",
    html: `
      <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; pointer-events: none;">
        <div style="position: absolute; width: 26px; height: 26px; border: 1.5px solid #10B981; border-radius: 50%; background: rgba(16, 185, 129, 0.15);"></div>
        <div style="position: absolute; width: 6px; height: 6px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981;"></div>
        <div style="position: absolute; top: 0; width: 1.5px; height: 6px; background: #10B981;"></div>
        <div style="position: absolute; bottom: 0; width: 1.5px; height: 6px; background: #10B981;"></div>
        <div style="position: absolute; left: 0; height: 1.5px; width: 6px; background: #10B981;"></div>
        <div style="position: absolute; right: 0; height: 1.5px; width: 6px; background: #10B981;"></div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

// Lightweight directional SVG wind vector arrow
function getWindArrowIcon(speed: number, direction: number) {
  const color = speed < 15 ? "#38BDF8" : speed < 30 ? "#10B981" : speed < 50 ? "#F59E0B" : "#EF4444";
  return L.divIcon({
    className: "wind-arrow-marker",
    html: `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 36px; height: 36px; transform: rotate(${direction}deg); filter: drop-shadow(0 0 3px rgba(0,0,0,0.8));">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

// Scientific color mapping functions
function getTemperatureColor(temp: number | null): string {
  if (temp === null) return "rgba(100, 116, 139, 0.2)";
  if (temp < 0) return "#1E40AF";
  if (temp < 10) return "#0284C7";
  if (temp < 18) return "#0D9488";
  if (temp < 24) return "#10B981";
  if (temp < 28) return "#EAB308";
  if (temp < 34) return "#F97316";
  return "#EF4444";
}

function getPrecipitationColor(precip: number | null): string {
  if (precip === null) return "rgba(100, 116, 139, 0.2)";
  if (precip <= 0.05) return "rgba(56, 189, 248, 0.04)";
  if (precip < 1.0) return "rgba(56, 189, 248, 0.45)";
  if (precip < 5.0) return "rgba(2, 132, 199, 0.65)";
  if (precip < 15.0) return "rgba(79, 70, 229, 0.75)";
  return "rgba(147, 51, 234, 0.85)";
}

function getCloudCoverColor(cover: number | null): string {
  if (cover === null) return "rgba(100, 116, 139, 0.2)";
  if (cover <= 10) return "rgba(148, 163, 184, 0.05)";
  if (cover <= 30) return "rgba(180, 195, 210, 0.2)";
  if (cover <= 60) return "rgba(200, 215, 230, 0.35)";
  if (cover <= 85) return "rgba(210, 220, 235, 0.5)";
  return "rgba(220, 230, 245, 0.65)";
}

function getDisagreementColor(spread: number | null): string {
  if (spread === null) return "rgba(100, 116, 139, 0.2)";
  if (spread < 0.5) return "#10B981";
  if (spread < 1.2) return "#38BDF8";
  if (spread < 2.5) return "#F59E0B";
  return "#EF4444";
}

function getWeightColor(weight: number | null): string {
  if (weight === null) return "rgba(100, 116, 139, 0.2)";
  if (weight <= 0.0) return "rgba(100, 116, 139, 0.3)";
  if (weight < 0.25) return "#38BDF8";
  if (weight < 0.5) return "#10B981";
  if (weight < 0.75) return "#F59E0B";
  return "#EF4444";
}

// Controller to smoothly pan map when selected location coordinates change
function RecenterOnLocation({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true });
  }, [lat, lon, map]);
  return null;
}

// Listener for user map clicks to select new coordinates
function MapInteractionListener({ onSelect }: { onSelect: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Forces Leaflet to recalculate size after mount to prevent tile squishing on mobile
function MapResizer() {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
}

export function WeatherMap({
  className = "",
  height = "h-[360px]",
  showLayerSlots = true,
  initialOverlay = "temperature",
  onSummaryUpdate,
}: WeatherMapProps) {
  const { location, setCoordinates } = useLocation();
  const { tempSymbol, windSymbol, convertTemp, convertTempDelta, convertWind } = useSettings();

  // Meteorological overlay state
  const [activeOverlay, setActiveOverlay] = useState<OverlayType>(initialOverlay);
  const [selectedModel, setSelectedModel] = useState<"ecmwf_ifs025" | "gfs_seamless" | "ecmwf_aifs025" | "blended_ensemble">("ecmwf_ifs025");
  const [validTime, setValidTime] = useState<string | null>(null);
  const [weightLeadTime, setWeightLeadTime] = useState<number>(24);

  // Spatial data state
  const [gridData, setGridData] = useState<GridResponse | null>(null);
  const [weightsGridData, setWeightsGridData] = useState<SpatialWeightGridResponse | SpatialLeadTimeWeightGridResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hudOpen, setHudOpen] = useState(true);

  // Regime state
  const [regimeData, setRegimeData] = useState<RegimeDefinition[] | null>(null);
  const [regimeStatus, setRegimeStatus] = useState<string>("LOADING");

  const stationMarkerIcon = useMemo(() => getCrosshairIcon(), []);

  const summaryUpdateRef = useRef(onSummaryUpdate);
  useEffect(() => {
    summaryUpdateRef.current = onSummaryUpdate;
  }, [onSummaryUpdate]);

  // Fetch regime data once on mount
  useEffect(() => {
    let ignore = false;
    async function fetchRegimes() {
      try {
        const res = await api.getRegimes();
        if (!ignore) {
          setRegimeData(res.regimes || []);
          setRegimeStatus(res.status);
        }
      } catch {
        if (!ignore) {
          setRegimeStatus("UNAVAILABLE");
        }
      }
    }
    fetchRegimes();
    return () => { ignore = true; };
  }, []);

  // Trigger grid fetch on coordinate or overlay change
  useEffect(() => {
    let ignore = false;
    async function run() {
      if (activeOverlay === "none" || activeOverlay === "uncertainty") {
        setGridData(null);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        let reqVariable = "temperature_2m";
        let reqModel = selectedModel;

        if (activeOverlay === "ensemble") {
          reqVariable = "temperature_2m";
          reqModel = "ensemble" as typeof selectedModel;
        } else if (activeOverlay === "temperature") {
          reqVariable = "temperature_2m";
          reqModel = selectedModel === "blended_ensemble" ? "ensemble" as typeof selectedModel : selectedModel;
        } else if (activeOverlay === "precipitation") {
          reqVariable = "precipitation";
          reqModel = selectedModel === "blended_ensemble" ? "ensemble" as typeof selectedModel : selectedModel;
        } else if (activeOverlay === "wind") {
          reqVariable = "wind";
          reqModel = selectedModel === "blended_ensemble" ? "ensemble" as typeof selectedModel : selectedModel;
        } else if (activeOverlay === "cloud_cover") {
          reqVariable = "cloud_cover";
          reqModel = selectedModel === "blended_ensemble" ? "ensemble" as typeof selectedModel : selectedModel;
        } else if (activeOverlay === "disagreement") {
          reqVariable = "temperature_2m";
          reqModel = "disagreement" as typeof selectedModel;
        }

        if (activeOverlay === "weights") {
          const res = await api.getWeightsGrid(
            location.latitude,
            location.longitude,
            "temperature_2m",
            5,
            0.25,
            weightLeadTime
          );
          if (!ignore) {
            setWeightsGridData(res);
            setLoading(false);
          }
        } else {
          const res = await api.getGrid(
            location.latitude,
            location.longitude,
            reqVariable,
            reqModel,
            validTime || undefined,
            5,
            0.25
          );

          if (!ignore) {
            setGridData(res);
            if (!validTime && res.valid_time) {
              setValidTime(res.valid_time);
            }
            if (summaryUpdateRef.current && res.ensemble_summary) {
              const lt = res.available_valid_times.length > 0 ? 
                  Math.floor((new Date(res.valid_time).getTime() - new Date(res.available_valid_times[0]).getTime()) / 3600000) : 0;
              summaryUpdateRef.current(res.ensemble_summary, {lat: location.latitude, lon: location.longitude}, lt);
            }
            setLoading(false);
          }
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load spatial meteorological field";
          setError(msg);
          setLoading(false);
        }
      }
    }

    run();
    return () => {
      ignore = true;
    };
  }, [location.latitude, location.longitude, activeOverlay, selectedModel, validTime, weightLeadTime]);

  // Time navigation handlers
  const availableTimes = gridData?.available_valid_times || [];
  const currentValidTimeIndex = availableTimes.indexOf(validTime || (gridData?.valid_time || ""));

  const handleStepTime = (delta: number) => {
    if (availableTimes.length === 0) return;
    const nextIdx = Math.max(0, Math.min(availableTimes.length - 1, (currentValidTimeIndex >= 0 ? currentValidTimeIndex : 0) + delta));
    const nextTime = availableTimes[nextIdx];
    setValidTime(nextTime);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value, 10);
    if (availableTimes[idx]) {
      setValidTime(availableTimes[idx]);
    }
  };

  // Format valid time for display
  const formatTimeDisplay = (timeStr: string | null) => {
    if (!timeStr) return "T+0h Live";
    try {
      const d = new Date(timeStr);
      return `${d.toISOString().replace(".000Z", "").replace("T", " ")} UTC`;
    } catch {
      return timeStr;
    }
  };

  // Layer button config for compact rendering
  const layerButtons: { key: OverlayType; label: string; icon: React.ReactNode }[] = [
    { key: "ensemble", label: "Ensemble", icon: <Layers className="w-3 h-3 text-ensemble" /> },
    { key: "temperature", label: "Temperature", icon: <Thermometer className="w-3 h-3" /> },
    { key: "precipitation", label: "Precip", icon: <CloudRain className="w-3 h-3" /> },
    { key: "cloud_cover", label: "Clouds", icon: <Cloud className="w-3 h-3" /> },
    { key: "wind", label: "Wind Flow", icon: <WindIcon className="w-3 h-3" /> },
    { key: "disagreement", label: "Spread", icon: <GitCompare className="w-3 h-3" /> },
    { key: "weights", label: "Weights", icon: <Crosshair className="w-3 h-3" /> },
    { key: "none", label: "Base Only", icon: null },
  ];

  return (
    <div className={`relative w-full ${height} bg-panel border border-border-subtle rounded-sm overflow-hidden flex flex-col font-mono text-xs ${className}`}>
      
      {/* Top-Left: Station Coordinate Telemetry HUD */}
      <div className="absolute top-2 left-2 z-[1000] bg-background/90 backdrop-blur-sm border border-border-subtle px-2.5 py-1.5 rounded-sm shadow-lg flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-ensemble">
          <Crosshair className="w-3.5 h-3.5" />
          <span className="font-bold text-white uppercase">{location.name}</span>
        </div>
        <div className="text-[11px] text-text-secondary border-l border-border-subtle pl-2 flex items-center gap-2">
          <span>{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E</span>
          {loading && <Loader2 className="w-3 h-3 text-ensemble animate-spin" />}
        </div>
      </div>

      {/* AIFS Null Safety Warning Banner */}
      {selectedModel === "ecmwf_aifs025" && activeOverlay !== "none" && (
        <div className="absolute top-11 left-2 z-[1000] bg-panel/95 border border-status-unavailable/60 text-status-unavailable px-3 py-1.5 rounded-sm shadow-xl flex items-center gap-2 max-w-lg text-[11px] animate-fade-in">
          <ShieldAlert className="w-4 h-4 shrink-0 text-status-unavailable" />
          <div>
            <strong className="block font-bold">ECMWF ECMWF AIFS · AI Model: NULL SAFETY ACTIVE</strong>
            <span className="text-text-secondary text-[10px]">
              Provider returned null values for all requested variables. Model dropped from blending pipeline without zero-substitution.
            </span>
          </div>
        </div>
      )}

      {/* Error Notice Banner */}
      {error && (
        <div className="absolute top-11 left-2 z-[1000] bg-panel/95 border border-status-unavailable text-status-unavailable px-3 py-1.5 rounded-sm shadow-xl flex items-center gap-2 max-w-md text-[11px]">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Floating Top-Right: Meteorological Layer & Model Control HUD */}
      {showLayerSlots && (
        <div className="absolute top-2 right-2 z-[1000] bg-background/95 backdrop-blur-sm border border-border-subtle p-2 rounded-sm shadow-2xl flex flex-col gap-2 max-w-[250px] text-[11px]">
          <div className="flex items-center justify-between pb-1 border-b border-border-subtle">
            <span className="flex items-center gap-1.5 font-bold text-white uppercase">
              <Layers className="w-3.5 h-3.5 text-ensemble" /> Weather Overlays
            </span>
            <button
              type="button"
              onClick={() => setHudOpen(!hudOpen)}
              className="text-[10px] text-text-secondary hover:text-white uppercase"
            >
              {hudOpen ? "Collapse" : "Expand"}
            </button>
          </div>

          {hudOpen && (
            <div className="space-y-2 mt-0.5">
              {/* Layer Selection */}
              <div>
                <span className="text-[10px] uppercase text-text-secondary block mb-1">Meteorological Field</span>
                <div className="grid grid-cols-2 gap-1">
                  {layerButtons.map((btn) => (
                    <button
                      key={btn.key}
                      type="button"
                      onClick={() => setActiveOverlay(btn.key)}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-sm text-[10px] border transition-colors ${
                        activeOverlay === btn.key
                          ? "bg-ensemble/20 border-ensemble text-ensemble font-bold"
                          : "bg-background border-border-subtle text-text-secondary hover:text-white"
                      }`}
                    >
                      {btn.icon}
                      <span>{btn.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Model Selection */}
              {activeOverlay !== "ensemble" && activeOverlay !== "disagreement" && activeOverlay !== "none" && activeOverlay !== "uncertainty" && (
                <div className="pt-1 border-t border-border-subtle">
                  <span className="text-[10px] uppercase text-text-secondary block mb-1">NWP / ML Model</span>
                  <div className="space-y-1">
                    <button type="button" onClick={() => setSelectedModel("ecmwf_ifs025")}
                      className={`w-full flex items-center justify-between px-2 py-1 rounded-sm text-[10px] border transition-colors text-left ${selectedModel === "ecmwf_ifs025" ? "bg-panel border-ensemble text-white font-semibold" : "bg-background border-border-subtle text-text-secondary hover:text-white"}`}>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-ifs)]" />ECMWF IFS (0.25°)</span>
                      <span className="text-[9px] text-status-available">PHYSICS</span>
                    </button>
                    <button type="button" onClick={() => setSelectedModel("gfs_seamless")}
                      className={`w-full flex items-center justify-between px-2 py-1 rounded-sm text-[10px] border transition-colors text-left ${selectedModel === "gfs_seamless" ? "bg-panel border-ensemble text-white font-semibold" : "bg-background border-border-subtle text-text-secondary hover:text-white"}`}>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-gfs)]" />NOAA GFS (0.25°)</span>
                      <span className="text-[9px] text-status-available">PHYSICS</span>
                    </button>
                    <button type="button" onClick={() => setSelectedModel("ecmwf_aifs025")}
                      className={`w-full flex items-center justify-between px-2 py-1 rounded-sm text-[10px] border transition-colors text-left ${selectedModel === "ecmwf_aifs025" ? "bg-panel border-status-unavailable text-status-unavailable font-semibold" : "bg-background border-border-subtle text-text-secondary hover:text-white"}`}>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-aifs)]" />ECMWF AIFS (0.25°)</span>
                      <span className="text-[9px] text-status-unavailable">NULL</span>
                    </button>
                    {activeOverlay === "weights" && (
                      <button type="button" onClick={() => setSelectedModel("blended_ensemble")}
                        className={`w-full flex items-center justify-between px-2 py-1 rounded-sm text-[10px] border transition-colors text-left ${selectedModel === "blended_ensemble" ? "bg-panel border-ensemble text-white font-semibold" : "bg-background border-border-subtle text-text-secondary hover:text-white"}`}>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-ensemble)]" />Balanced Output</span>
                        <span className="text-[9px] text-ensemble">ALL</span>
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Time Control Scrub Bar */}
              {availableTimes.length > 0 && activeOverlay !== "none" && activeOverlay !== "uncertainty" && (
                <div className="pt-1.5 border-t border-border-subtle space-y-1">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="flex items-center gap-1 text-text-secondary">
                      <Clock className="w-3 h-3 text-ensemble" /> Valid Time
                    </span>
                    <span className="text-white font-bold">
                      {formatTimeDisplay(validTime || gridData?.valid_time || null)}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button type="button" onClick={() => handleStepTime(-1)} disabled={currentValidTimeIndex <= 0}
                      className="p-1 bg-background border border-border-subtle hover:text-white disabled:opacity-30 rounded-sm" title="Step back 1 hour">
                      <ChevronLeft className="w-3 h-3" />
                    </button>
                    <input
                      type="range"
                      min={0}
                      max={Math.max(0, availableTimes.length - 1)}
                      value={currentValidTimeIndex >= 0 ? currentValidTimeIndex : 0}
                      onChange={handleSliderChange}
                      className="w-full accent-ensemble h-1 bg-background border border-border-subtle rounded-sm cursor-pointer"
                    />
                    <button type="button" onClick={() => handleStepTime(1)} disabled={currentValidTimeIndex >= availableTimes.length - 1}
                      className="p-1 bg-background border border-border-subtle hover:text-white disabled:opacity-30 rounded-sm" title="Step forward 1 hour">
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}

              {/* Lead Time Selector for Weights */}
              {activeOverlay === "weights" && (
                <div className="pt-1.5 border-t border-border-subtle space-y-1">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="flex items-center gap-1 text-text-secondary">
                      <Clock className="w-3 h-3 text-ensemble" /> Lead Time Target
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-1 mt-1">
                    {[24, 48, 72, 96, 120, 144, 168].map((lt) => (
                      <button
                        key={lt}
                        type="button"
                        onClick={() => setWeightLeadTime(lt)}
                        className={`px-1.5 py-0.5 rounded-sm text-[10px] border transition-colors ${
                          weightLeadTime === lt
                            ? "bg-ensemble/20 border-ensemble text-ensemble font-bold"
                            : "bg-background border-border-subtle text-text-secondary hover:text-white"
                        }`}
                      >
                        {lt}h
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Regime Context (only show when data available) */}
              {regimeData && regimeData.length > 0 && regimeStatus === "AVAILABLE" && (
                <div className="pt-1.5 border-t border-border-subtle">
                  <span className="text-[10px] uppercase text-text-secondary flex items-center gap-1 mb-1">
                    <Zap className="w-3 h-3 text-ensemble" /> Weather Regimes
                  </span>
                  <div className="space-y-0.5">
                    {regimeData.map((r) => (
                      <div key={r.regime_id} className="bg-background border border-border-subtle px-2 py-1 rounded-sm text-[9px]">
                        <span className="text-ensemble font-bold">REGIME {r.regime_id}</span>
                        <span className="text-text-secondary ml-1.5">{r.description}</span>
                        <span className="text-text-muted ml-1">({r.sample_count} samples)</span>
                      </div>
                    ))}
                  </div>
                  <div className="text-[8px] text-text-muted mt-0.5">
                    Source: {regimeData[0]?.provenance} | {regimeData[0]?.model_version}
                  </div>
                </div>
              )}

              {/* Probabilistic Panel */}
              {(activeOverlay === "temperature" || activeOverlay === "precipitation") && selectedModel !== "blended_ensemble" && (
                <div className="pt-2 border-t border-border-subtle">
                  <ProbabilisticPanel 
                    latitude={location.latitude}
                    longitude={location.longitude}
                    variable={activeOverlay === "temperature" ? "temperature_2m" : "precipitation"}
                    horizonHours={availableTimes.length > 0 && currentValidTimeIndex >= 0 ? 
                      Math.floor((new Date(availableTimes[currentValidTimeIndex]).getTime() - new Date(availableTimes[0]).getTime()) / 3600000) : 0
                    }
                    model={selectedModel}
                  />
                  <ExtremesPanel
                    latitude={location.latitude}
                    longitude={location.longitude}
                    horizonHours={availableTimes.length > 0 && currentValidTimeIndex >= 0 ? 
                      Math.floor((new Date(availableTimes[currentValidTimeIndex]).getTime() - new Date(availableTimes[0]).getTime()) / 3600000) : 0
                    }
                    model={selectedModel}
                  />
                  <ForecastBustPanel
                    latitude={location.latitude}
                    longitude={location.longitude}
                    locationName={location.name}
                    horizonHours={availableTimes.length > 0 && currentValidTimeIndex >= 0 ? 
                      Math.floor((new Date(availableTimes[currentValidTimeIndex]).getTime() - new Date(availableTimes[0]).getTime()) / 3600000) : 0
                    }
                    model={selectedModel}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Ensemble Uncertainty Notice Modal */}
      {activeOverlay === "uncertainty" && (
        <div className="absolute inset-0 z-[1010] bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel border border-border-subtle p-5 rounded-sm max-w-md text-center space-y-3 shadow-2xl">
            <div className="w-10 h-10 rounded-full bg-ensemble/10 border border-ensemble/30 text-ensemble flex items-center justify-center mx-auto">
              <Info className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-white uppercase">Spatial Ensemble Uncertainty</h3>
            <p className="text-[11px] text-text-secondary leading-relaxed">
              Spatial ensemble uncertainty data is not currently available from single-deterministic grid streams. Requires multi-member spatial ensemble field integration (e.g., ECMWF ENS 51-member spread).
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setActiveOverlay("temperature")}
                className="bg-ensemble text-slate-950 px-3 py-1.5 rounded-sm font-bold text-xs hover:bg-ensemble/90"
              >
                Return to Temperature Field
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Bottom-Left: Scientific Legend HUD */}
      {activeOverlay !== "none" && activeOverlay !== "uncertainty" && (
        <div className="absolute bottom-9 left-2 z-[1000] bg-background/95 backdrop-blur-sm border border-border-subtle px-3 py-2 rounded-sm shadow-xl text-[10px] space-y-1.5 max-w-xs animate-fade-in">
          {/* Ensemble Legend */}
          {activeOverlay === "ensemble" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span className="flex items-center gap-1.5 text-ensemble"><Layers className="w-3.5 h-3.5" /> BLENDED ENSEMBLE</span>
                <span className="text-ensemble">{tempSymbol}</span>
              </div>
              <div className="text-[9px] text-text-secondary mt-0.5">Formula: sum(weight_i × val_i) | Normalized over valid models</div>
              <div className="w-56 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "#38BDF8" }} className="flex-1" title="<0°" />
                <div style={{ backgroundColor: "#2DD4BF" }} className="flex-1" title="0-10°" />
                <div style={{ backgroundColor: "#34D399" }} className="flex-1" title="10-18°" />
                <div style={{ backgroundColor: "#A3E635" }} className="flex-1" title="18-24°" />
                <div style={{ backgroundColor: "#FBBF24" }} className="flex-1" title="24-28°" />
                <div style={{ backgroundColor: "#FB923C" }} className="flex-1" title="28-34°" />
                <div style={{ backgroundColor: "#F87171" }} className="flex-1" title=">34°" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>&lt;0°</span><span>10°</span><span>18°</span><span>24°</span><span>28°</span><span>34°+</span>
              </div>
              <div className="text-[8.5px] text-text-secondary/80 mt-1">Weights: ECMWF IFS (73%), NOAA GFS (27%) | ECMWF AIFS · AI Model: Excluded (0%)</div>
            </div>
          )}

          {/* Temperature Legend */}
          {activeOverlay === "temperature" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>TEMPERATURE 2M</span><span className="text-ensemble">{tempSymbol}</span>
              </div>
              <div className="w-48 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "#1E40AF" }} className="flex-1" title="<0°C" />
                <div style={{ backgroundColor: "#0284C7" }} className="flex-1" title="0-10°C" />
                <div style={{ backgroundColor: "#0D9488" }} className="flex-1" title="10-18°C" />
                <div style={{ backgroundColor: "#10B981" }} className="flex-1" title="18-24°C" />
                <div style={{ backgroundColor: "#EAB308" }} className="flex-1" title="24-28°C" />
                <div style={{ backgroundColor: "#F97316" }} className="flex-1" title="28-34°C" />
                <div style={{ backgroundColor: "#EF4444" }} className="flex-1" title=">34°C" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>&lt;0°</span><span>10°</span><span>18°</span><span>24°</span><span>28°</span><span>34°+</span>
              </div>
            </div>
          )}

          {/* Precipitation Legend */}
          {activeOverlay === "precipitation" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>PRECIPITATION RATE</span><span className="text-ensemble">mm</span>
              </div>
              <div className="w-48 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "rgba(56, 189, 248, 0.1)" }} className="flex-1" title="0 mm (Dry)" />
                <div style={{ backgroundColor: "#38BDF8" }} className="flex-1" title="0.1 - 1.0 mm" />
                <div style={{ backgroundColor: "#0284C7" }} className="flex-1" title="1.0 - 5.0 mm" />
                <div style={{ backgroundColor: "#4F46E5" }} className="flex-1" title="5.0 - 15.0 mm" />
                <div style={{ backgroundColor: "#9333EA" }} className="flex-1" title=">15.0 mm" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>0</span><span>1.0</span><span>5.0</span><span>15.0+</span>
              </div>
              <div className="text-[8px] text-text-muted italic mt-0.5">Animated visualization of forecast precipitation field — not radar</div>
            </div>
          )}

          {/* Cloud Cover Legend */}
          {activeOverlay === "cloud_cover" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>FORECAST CLOUD COVER</span><span className="text-ensemble">%</span>
              </div>
              <div className="w-48 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "rgba(148, 163, 184, 0.05)" }} className="flex-1" title="0-10% Clear" />
                <div style={{ backgroundColor: "rgba(180, 195, 210, 0.3)" }} className="flex-1" title="10-30% Partly" />
                <div style={{ backgroundColor: "rgba(200, 215, 230, 0.5)" }} className="flex-1" title="30-60% Mostly" />
                <div style={{ backgroundColor: "rgba(210, 220, 235, 0.65)" }} className="flex-1" title="60-85% Overcast" />
                <div style={{ backgroundColor: "rgba(220, 230, 245, 0.8)" }} className="flex-1" title="85-100% Complete" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>0%</span><span>30%</span><span>60%</span><span>85%</span><span>100%</span>
              </div>
              <div className="text-[8px] text-text-muted italic mt-0.5">Forecast cloud-cover visualization — not satellite imagery</div>
            </div>
          )}

          {/* Wind Legend */}
          {activeOverlay === "wind" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>10M SURFACE WIND</span><span className="text-ensemble">km/h</span>
              </div>
              <div className="w-48 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "#38BDF8" }} className="flex-1" title="<15 km/h (Gentle)" />
                <div style={{ backgroundColor: "#10B981" }} className="flex-1" title="15-30 km/h (Moderate)" />
                <div style={{ backgroundColor: "#F59E0B" }} className="flex-1" title="30-50 km/h (Strong)" />
                <div style={{ backgroundColor: "#EF4444" }} className="flex-1" title=">50 km/h (Gale)" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>&lt;15</span><span>30</span><span>50+</span>
              </div>
              <div className="text-[8px] text-text-muted italic mt-0.5">Animated wind flow from real forecast wind_speed + wind_direction</div>
            </div>
          )}

          {/* Model Spread Legend */}
          {activeOverlay === "disagreement" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>MODEL SPREAD: max(valid) − min(valid)</span><span className="text-ensemble">{tempSymbol}</span>
              </div>
              <div className="text-[9px] text-text-secondary mt-0.5">Active models: ECMWF IFS vs NOAA GFS (|IFS − GFS|)</div>
              <div className="w-56 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "#10B981" }} className="flex-1" title="<0.5°" />
                <div style={{ backgroundColor: "#38BDF8" }} className="flex-1" title="0.5-1.2°" />
                <div style={{ backgroundColor: "#F59E0B" }} className="flex-1" title="1.2-2.5°" />
                <div style={{ backgroundColor: "#EF4444" }} className="flex-1" title=">2.5°" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>0.0°</span><span>0.5°</span><span>1.2°</span><span>2.5°+</span>
              </div>
              <div className="text-[8.5px] text-amber-400/90 mt-1 italic">High spread visualization threshold: {convertTempDelta(3.5).toFixed(1)}{tempSymbol}</div>
            </div>
          )}

          {/* Model Weights Legend */}
          {activeOverlay === "weights" && (
            <div>
              <div className="flex items-center justify-between text-white font-bold">
                <span>SPATIAL MODEL WEIGHTS</span><span className="text-ensemble">%</span>
              </div>
              <div className="text-[9px] text-text-secondary mt-0.5">
                Model: {selectedModel === "blended_ensemble" ? "All Evaluated Models" : selectedModel}
              </div>
              <div className="w-48 h-2.5 rounded-sm mt-1 flex overflow-hidden border border-border-subtle">
                <div style={{ backgroundColor: "rgba(100, 116, 139, 0.3)" }} className="w-[10%]" title="0%" />
                <div style={{ backgroundColor: "#38BDF8" }} className="flex-1" title="0 - 25%" />
                <div style={{ backgroundColor: "#10B981" }} className="flex-1" title="25 - 50%" />
                <div style={{ backgroundColor: "#F59E0B" }} className="flex-1" title="50 - 75%" />
                <div style={{ backgroundColor: "#EF4444" }} className="flex-1" title="75 - 100%" />
              </div>
              <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
              </div>
              {weightsGridData?.coverage_disclosure && (
                <div className="text-[8.5px] text-amber-400/90 mt-1 italic">{weightsGridData.coverage_disclosure}</div>
              )}
            </div>
          )}

          <div className="text-[9px] text-text-secondary/75 pt-1 border-t border-border-subtle flex items-center justify-between">
            <span>NWP native grid: 0.25° (~28 km latitude spacing)</span>
            <span>Forecast model field — not station observation</span>
          </div>
        </div>
      )}

      {/* Interactive Leaflet Map Container */}
      <div className="flex-1 w-full h-full">
        <MapContainer
          center={[location.latitude, location.longitude]}
          zoom={7}
          minZoom={2}
          maxZoom={18}
          scrollWheelZoom={false}
          style={{ width: "100%", height: "100%", backgroundColor: "#0F172A" }}
        >
          {/* Base Geographic Layer: OpenStreetMap Standard Raster Tiles */}
          <TileLayer
            className="osm-tiles"
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>'
            maxZoom={19}
          />

          {/* Canvas-based Cloud Cover Layer */}
          {activeOverlay === "cloud_cover" && gridData && (
            <CloudCoverLayer cells={gridData.cells} visible={activeOverlay === "cloud_cover"} />
          )}

          {/* Canvas-based Animated Wind Flow Layer */}
          {activeOverlay === "wind" && gridData && (
            <WindFlowLayer cells={gridData.cells} visible={activeOverlay === "wind"} />
          )}

          {/* Canvas-based Animated Precipitation Layer */}
          {activeOverlay === "precipitation" && gridData && (
            <PrecipitationLayer cells={gridData.cells} visible={activeOverlay === "precipitation"} />
          )}

          {/* Real Meteorological Grid Cells: Temperature, Precipitation, Cloud Cover, Disagreement */}
          {activeOverlay !== "none" &&
            activeOverlay !== "uncertainty" &&
            activeOverlay !== "weights" &&
            gridData?.cells.map((cell: GridCellAPI, idx: number) => {
              let fillColor = "transparent";
              let fillOpacity = 0.55;

              if (activeOverlay === "ensemble") {
                fillColor = getTemperatureColor(cell.value);
                fillOpacity = cell.value !== null ? 0.65 : 0.15;
              } else if (activeOverlay === "temperature") {
                fillColor = getTemperatureColor(cell.value);
                fillOpacity = cell.value !== null ? 0.6 : 0.15;
              } else if (activeOverlay === "precipitation") {
                fillColor = getPrecipitationColor(cell.value);
                fillOpacity = cell.value !== null && cell.value > 0.05 ? 0.7 : 0.08;
              } else if (activeOverlay === "cloud_cover") {
                fillColor = getCloudCoverColor(cell.value);
                fillOpacity = cell.value !== null ? 0.55 : 0.1;
              } else if (activeOverlay === "wind") {
                // Wind cells rendered by canvas layer + arrows below; rectangles provide tooltip
                fillColor = "transparent";
                fillOpacity = 0.01;
              } else if (activeOverlay === "disagreement") {
                fillColor = getDisagreementColor(cell.value);
                fillOpacity = cell.value !== null ? 0.65 : 0.15;
              }

              return (
                <Rectangle
                  key={`cell-${cell.latitude}-${cell.longitude}-${idx}`}
                  bounds={cell.bounds}
                  pathOptions={{
                    color: cell.value !== null ? "rgba(255,255,255,0.2)" : "rgba(239, 68, 68, 0.4)",
                    weight: 0.8,
                    dashArray: cell.value === null ? "4, 4" : undefined,
                    fillColor,
                    fillOpacity,
                  }}
                >
                  <Tooltip sticky direction="top" className="scientific-map-tooltip">
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="font-bold text-white uppercase tracking-wider flex items-center justify-between gap-3">
                        <span>{activeOverlay === "ensemble" ? "Adaptive Ensemble" : activeOverlay === "disagreement" ? "Model Spread" : cell.model}</span>
                        <span className="text-ensemble font-bold">
                          {cell.value !== null ? `${cell.value} ${cell.unit}` : "UNAVAILABLE"}
                        </span>
                      </div>
                      <div className="text-[10px] text-text-secondary border-t border-border-subtle pt-1 space-y-0.5">
                        {activeOverlay === "ensemble" && (
                          <>
                            <div className="text-ensemble font-semibold">Synthesis: sum(w_i × val_i)</div>
                            <div>Weights: IFS (73%), GFS (27%) | AIFS (0%)</div>
                            {cell.contributing_values && (
                              <div>IFS: {cell.contributing_values["ecmwf_ifs025"] != null ? `${convertTemp(cell.contributing_values["ecmwf_ifs025"]).toFixed(1)}${tempSymbol}` : "—"} | GFS: {cell.contributing_values["gfs_seamless"] != null ? `${convertTemp(cell.contributing_values["gfs_seamless"]).toFixed(1)}${tempSymbol}` : "—"}</div>
                            )}
                            {cell.model_spread !== null && cell.model_spread !== undefined && (
                              <div className="text-amber-400/90">
                                Model Spread: {convertTempDelta(cell.model_spread).toFixed(1)}{tempSymbol}
                                {cell.pairwise_difference !== null && cell.pairwise_difference !== undefined && ` (|IFS − GFS|: ${convertTempDelta(cell.pairwise_difference).toFixed(1)}${tempSymbol})`}
                              </div>
                            )}
                          </>
                        )}
                        {activeOverlay === "disagreement" && (
                          <>
                            <div>Metric: max(valid) − min(valid)</div>
                            <div>Active Pair: |ECMWF IFS − NOAA GFS|</div>
                            <div className="text-amber-400/80 text-[9px]">High spread vis threshold: {convertTempDelta(3.5).toFixed(1)}{tempSymbol}</div>
                          </>
                        )}
                        {activeOverlay === "cloud_cover" && (
                          <div className="text-text-muted italic text-[9px]">Forecast cloud-cover visualization</div>
                        )}
                        {activeOverlay === "wind" && cell.wind_speed !== null && cell.wind_speed !== undefined && (
                          <div>Direction: {cell.wind_direction}° | Speed: {convertWind(cell.wind_speed).toFixed(1)} {windSymbol}</div>
                        )}
                        <div>Grid Cell: {cell.latitude.toFixed(4)}°N, {cell.longitude.toFixed(4)}°E (0.25° ~28 km lat spacing)</div>
                        <div>Valid Time: {cell.valid_time} UTC</div>
                        <div>Source: {cell.source}</div>
                        <div className="text-text-secondary/70 italic text-[9px] mt-0.5">
                          Forecast model field — not station observation
                        </div>
                      </div>
                    </div>
                  </Tooltip>
                </Rectangle>
              );
            })}

          {/* Wind Arrows (static directional markers, complementing the animated canvas flow) */}
          {activeOverlay === "wind" &&
            gridData?.cells.map((cell: GridCellAPI, idx: number) => {
              if (typeof cell.wind_speed !== "number" || typeof cell.wind_direction !== "number") return null;
              const windIcon = getWindArrowIcon(cell.wind_speed, cell.wind_direction);
              return (
                <Marker
                  key={`wind-${cell.latitude}-${cell.longitude}-${idx}`}
                  position={[cell.latitude, cell.longitude]}
                  icon={windIcon}
                >
                  <Tooltip sticky direction="top" className="scientific-map-tooltip">
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="font-bold text-white uppercase tracking-wider flex items-center justify-between gap-3">
                        <span>{cell.model}</span>
                        <span className="text-ensemble font-bold">{cell.wind_speed} km/h</span>
                      </div>
                      <div className="text-[10px] text-text-secondary border-t border-border-subtle pt-1 space-y-0.5">
                        <div>Direction: {cell.wind_direction}° (Compass vector)</div>
                        <div>Grid Cell: {cell.latitude.toFixed(4)}°N, {cell.longitude.toFixed(4)}°E</div>
                        <div>Valid Time: {cell.valid_time} UTC</div>
                        <div>Source: {cell.source}</div>
                        <div className="text-text-secondary/70 italic text-[9px] mt-0.5">
                          Forecast model field — not station observation
                        </div>
                      </div>
                    </div>
                  </Tooltip>
                </Marker>
              );
            })}

          {/* Spatial Model Weights Grid Cells */}
          {activeOverlay === "weights" &&
            weightsGridData?.cells
              .filter((cell) => cell.model === (selectedModel === "blended_ensemble" ? "ecmwf_ifs025" : selectedModel))
              .map((cell, idx) => {
              // Cell may be SpatialWeightRecord or SpatialLeadTimeWeightRecord
              const cellRecord = cell as unknown as Record<string, unknown>;
              const weight = (cellRecord.weight as number | null) ?? null;
              const fillColor = getWeightColor(weight);
              const fillOpacity = weight !== null ? 0.7 : 0.15;

              return (
                <Rectangle
                  key={`weight-${cell.latitude}-${cell.longitude}-${idx}`}
                  bounds={cell.bounds}
                  pathOptions={{
                    color: weight !== null ? "rgba(255,255,255,0.25)" : "rgba(100, 116, 139, 0.4)",
                    weight: 1,
                    dashArray: weight === null ? "4, 4" : undefined,
                    fillColor,
                    fillOpacity,
                  }}
                >
                  <Tooltip sticky direction="top" className="scientific-map-tooltip">
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="font-bold text-white uppercase tracking-wider flex items-center justify-between gap-3">
                        <span>{selectedModel === "blended_ensemble" ? "All Evaluated Models" : cell.model}</span>
                        <span className="text-ensemble font-bold">
                          {weight !== null ? `${(weight * 100).toFixed(1)}%` : "0% (UNAVAILABLE)"}
                        </span>
                      </div>
                      <div className="text-[10px] text-text-secondary border-t border-border-subtle pt-1 space-y-0.5">
                        <div className="text-ensemble font-semibold">Weight Allocation</div>
                        <div>Status: {cell.status}</div>
                        {typeof cellRecord.rmse === "number" && (
                          <div>RMSE: {(cellRecord.rmse as number).toFixed(3)}</div>
                        )}
                        {typeof cellRecord.historical_metric === "number" && (
                          <div>{String(cellRecord.metric_name)}: {(cellRecord.historical_metric as number).toFixed(3)}</div>
                        )}
                        {typeof cellRecord.lead_time_hours === "number" && (
                          <div>Target Lead Time: {cellRecord.lead_time_hours}h</div>
                        )}
                        <div>Evaluation Period: {cell.evaluation_period}</div>
                        <div>Samples: {cell.sample_count}</div>
                        <div>Reference: {cell.reference_source}</div>
                        <div>Grid Cell: {cell.latitude.toFixed(4)}°N, {cell.longitude.toFixed(4)}°E (0.25° ~28 km lat spacing)</div>
                        {typeof cellRecord.coverage_type === "string" && <div>Coverage Type: {cellRecord.coverage_type}</div>}
                      </div>
                    </div>
                  </Tooltip>
                </Rectangle>
              );
            })}

          {/* Active Station Spatial Grid Cell Footprint */}
          <Circle
            center={[location.latitude, location.longitude]}
            radius={14000}
            pathOptions={{
              color: "#10B981",
              weight: 1.5,
              dashArray: "3, 5",
              fillColor: "#10B981",
              fillOpacity: 0.04,
            }}
          />

          {/* Active Station Targeting Crosshair Marker */}
          <Marker
            position={[location.latitude, location.longitude]}
            icon={stationMarkerIcon}
          />

          {/* Smooth Recenter Controller */}
          <RecenterOnLocation lat={location.latitude} lon={location.longitude} />

          {/* Force Resize on Mount for Mobile */}
          <MapResizer />

          {/* Map Click Listener */}
          <MapInteractionListener
            onSelect={(lat, lon) => {
              setCoordinates(lat, lon);
            }}
          />
        </MapContainer>
      </div>

      {/* Bottom Status & Attribution Strip */}
      <div className="bg-background/90 border-t border-border-subtle px-3 py-2 text-[9px] sm:text-[10px] text-text-secondary flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 sm:gap-0 z-10 shrink-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span>Click map to select target coordinates</span>
          <span className="text-border-subtle hidden sm:inline">|</span>
          <span>© OpenStreetMap contributors</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
          {activeOverlay !== "none" && (
            <span className="text-white font-semibold">
              FIELD: <span className="text-ensemble uppercase">{activeOverlay === "cloud_cover" ? "CLOUD COVER" : activeOverlay}</span>
            </span>
          )}
          <span className="text-ensemble font-semibold tracking-wider">
            BASEMAP: OPENSTREETMAP
          </span>
        </div>
      </div>
    </div>
  );
}

export default WeatherMap;
