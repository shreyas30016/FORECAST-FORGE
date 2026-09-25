import React, { useState, useEffect } from "react";
import { ProbabilisticForecast, EventProbabilityResult } from "@/types/api";
import { API_BASE_URL } from "@/lib/api";

interface ProbabilisticPanelProps {
  latitude: number;
  longitude: number;
  variable: string;
  horizonHours: number;
  model: string;
}

export function ProbabilisticPanel({ latitude, longitude, variable, horizonHours, model }: ProbabilisticPanelProps) {
  const [forecasts, setForecasts] = useState<ProbabilisticForecast[]>([]);
  const [events, setEvents] = useState<EventProbabilityResult[]>([]);
  const [loading, setLoading] = useState(false);
  
  // A helper function to fetch probabilistic data
  useEffect(() => {
    let ignore = false;
    
    async function fetchData() {
      setLoading(true);
      try {
        // Fetch distribution
        const res = await fetch(`${API_BASE_URL}/probabilistic/forecast?latitude=${latitude}&longitude=${longitude}&variable=${variable}&horizon_hours=${horizonHours}&model=${model}`);
        if (res.ok && !ignore) {
          const data = await res.json();
          setForecasts(data);
        }
        
        // Fetch specific events based on variable
        if (variable === "precipitation") {
          const thresholds = [5.0, 10.0, 25.0];
          const eventPromises = thresholds.map(t => 
            fetch(`${API_BASE_URL}/probabilistic/probability?latitude=${latitude}&longitude=${longitude}&variable=${variable}&operator=${encodeURIComponent(">=")}&threshold=${t}&horizon_hours=${horizonHours}&model=${model}`).then(r => r.json())
          );
          
          const eventResults = await Promise.all(eventPromises);
          if (!ignore) {
            // Flatten the results
            const flatEvents = eventResults.flat().filter(e => !e.detail && e.status === "AVAILABLE");
            setEvents(flatEvents);
          }
        } else {
          if (!ignore) setEvents([]);
        }
      } catch (err) {
        console.error("Failed to fetch probabilistic data", err);
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    
    fetchData();
    return () => { ignore = true; };
  }, [latitude, longitude, variable, horizonHours, model]);
  
  if (loading) {
    return <div className="text-xs text-text-secondary animate-pulse py-2">Loading ensemble members...</div>;
  }
  
  if (!forecasts.length) {
    return null;
  }
  
  // Get the first matching forecast for the requested horizon
  const targetForecast = forecasts.find(f => f.lead_time_hours === horizonHours) || forecasts[0];
  
  if (targetForecast.status === "INSUFFICIENT_DATA") {
    return (
      <div className="mt-3 p-3 bg-surface-raised rounded-md border border-border-subtle">
        <h4 className="text-[10px] uppercase font-bold tracking-wider text-text-secondary mb-1">Ensemble Distribution</h4>
        <div className="text-xs text-error">Insufficient ensemble members available.</div>
      </div>
    );
  }

  const formatVal = (val: number | null) => val !== null ? val.toFixed(1) : "--";

  return (
    <div className="mt-3 p-3 bg-surface-raised rounded-md border border-border-subtle">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[10px] uppercase font-bold tracking-wider text-text-secondary">Ensemble Range ({targetForecast.valid_member_count} members)</h4>
        <div className="text-[9px] text-text-tertiary">{targetForecast.provenance}</div>
      </div>
      
      {/* Quantile visualization */}
      <div className="space-y-3">
        <div className="relative h-6 bg-surface border border-border-subtle rounded flex items-center px-2">
          {targetForecast.p10 !== null && targetForecast.p90 !== null && targetForecast.p50 !== null && (
            <>
              {/* Range bar background (10th to 90th) */}
              <div 
                className="absolute h-2 bg-blue-500/20 rounded-full" 
                style={{ 
                  left: "10%", 
                  right: "10%" 
                }}
              />
              
              {/* Median tick */}
              <div 
                className="absolute h-4 w-1 bg-blue-400 z-10" 
                style={{ 
                  left: "50%", 
                  transform: "translateX(-50%)" 
                }}
              />
              
              {/* Labels */}
              <div className="absolute left-2 text-[10px] font-mono text-blue-300">
                P10: {formatVal(targetForecast.p10)}
              </div>
              <div className="absolute right-2 text-[10px] font-mono text-blue-300">
                P90: {formatVal(targetForecast.p90)}
              </div>
            </>
          )}
        </div>
        
        <div className="flex justify-between text-xs">
          <div><span className="text-text-tertiary">Mean:</span> {formatVal(targetForecast.mean)}</div>
          <div><span className="text-text-tertiary">Median (P50):</span> {formatVal(targetForecast.median)}</div>
          <div><span className="text-text-tertiary">Spread:</span> ±{formatVal(targetForecast.spread)}</div>
        </div>
        
        {/* Event probabilities */}
        {events.length > 0 && (
          <div className="pt-2 border-t border-border-subtle">
            <h5 className="text-[10px] text-text-secondary mb-1">Event Probabilities</h5>
            <div className="space-y-1">
              {/* De-duplicate events by threshold just in case multiple matching lead times came back */}
              {Array.from(new Map(events.map(e => [e.threshold, e])).values()).map((e, idx) => (
                <div key={idx} className="flex justify-between text-[11px] font-mono">
                  <span>{e.variable} {e.operator} {e.threshold}</span>
                  <span className={e.probability && e.probability > 0.5 ? "text-amber-400 font-bold" : "text-blue-300"}>
                    {e.probability !== null ? `${(e.probability * 100).toFixed(0)}%` : "--"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
