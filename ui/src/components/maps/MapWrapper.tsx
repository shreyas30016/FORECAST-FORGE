"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

import { EnsembleSummaryAPI } from "@/types/api";

interface WeatherMapProps {
  className?: string;
  height?: string;
  showLayerSlots?: boolean;
  initialOverlay?: "ensemble" | "temperature" | "precipitation" | "wind" | "cloud_cover" | "disagreement" | "uncertainty" | "none";
  onSummaryUpdate?: (summary: EnsembleSummaryAPI | null, location?: {lat: number, lon: number}, leadTime?: number) => void;
}

// Dynamically import WeatherMap with SSR disabled to prevent Leaflet window access errors
const WeatherMapDynamic = dynamic(() => import("./WeatherMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[360px] bg-panel border border-border-subtle rounded-sm flex flex-col items-center justify-center font-mono text-xs text-text-secondary gap-2">
      <Loader2 className="w-5 h-5 text-ensemble animate-spin" />
      <span>INITIALIZING GEOSPATIAL MAP ENGINE...</span>
    </div>
  ),
});

export function MapWrapper(props: WeatherMapProps) {
  return <WeatherMapDynamic {...props} />;
}

export default MapWrapper;
