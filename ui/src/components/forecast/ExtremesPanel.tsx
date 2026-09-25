import React, { useState, useEffect } from "react";
import { useSettings } from "@/context/SettingsContext";
import { API_BASE_URL } from "@/lib/api";

interface ExtremeEvent {
  event_type: string;
  threshold: number;
  probability: number | null;
  probability_method: string;
  lead_time_hours: number;
  valid_time: string;
  location: string;
  ensemble_member_count: number;
  valid_member_count: number;
  active_models: string[];
  spatial_context: {
    latitude: number;
    longitude: number;
    is_supported: boolean;
  };
  regime: {
    current_regime: string;
    regime_id: number;
    regime_description: string;
    regime_sample_count: number;
  } | null;
  status: string;
  provenance: string;
}

interface ExtremesPanelProps {
  latitude: number;
  longitude: number;
  horizonHours: number;
  model: string;
}

export function ExtremesPanel({ latitude, longitude, horizonHours, model }: ExtremesPanelProps) {
  const { convertTemp, convertWind, tempSymbol, windSymbol } = useSettings();
  const [events, setEvents] = useState<ExtremeEvent[]>([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    let ignore = false;
    
    async function fetchData() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/extremes/guidance?latitude=${latitude}&longitude=${longitude}&lead_time_hours=${horizonHours}&model=${model}`);
        if (res.ok && !ignore) {
          const data = await res.json();
          setEvents(data);
        }
      } catch (err) {
        console.error("Failed to fetch extreme weather guidance", err);
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    
    fetchData();
    return () => { ignore = true; };
  }, [latitude, longitude, horizonHours, model]);
  
  if (loading) {
    return <div className="text-xs text-text-secondary animate-pulse py-2">Loading extreme weather guidance...</div>;
  }
  
  if (!events.length) {
    return null;
  }

  return (
    <div className="mt-3 p-3 bg-surface-raised rounded-md border border-border-subtle">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[10px] uppercase font-bold tracking-wider text-text-secondary">Extreme Weather Guidance</h4>
      </div>
      
      <div className="space-y-3">
        {events.map((e, idx) => (
          <div key={idx} className="flex flex-col text-[11px] font-mono border-b border-border-subtle pb-2 last:border-0 last:pb-0">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold">{e.event_type}</span>
              <span className={e.probability !== null && e.probability >= 0.5 ? "text-error font-bold" : "text-ensemble font-bold"}>
                {e.probability !== null ? `${(e.probability * 100).toFixed(0)}%` : "--"}
              </span>
            </div>
            <div className="text-[9px] text-text-tertiary">
              Threshold: &gt;= {e.event_type === "Extreme Temperature" 
                ? `${convertTemp(e.threshold).toFixed(1)} ${tempSymbol}` 
                : e.event_type === "Heavy Rain" 
                ? `${e.threshold} mm` 
                : `${convertWind(e.threshold).toFixed(1)} ${windSymbol}`}
            </div>
            
            {e.regime && (
              <div className="mt-1 bg-background border border-border-subtle px-2 py-1 rounded-sm text-[9px] text-ensemble">
                {e.regime.current_regime}: {e.regime.regime_description}
              </div>
            )}
            
            {e.status === "INSUFFICIENT_DATA" && (
              <div className="text-[9px] text-error mt-1">Insufficient members ({e.valid_member_count}/{e.ensemble_member_count})</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
