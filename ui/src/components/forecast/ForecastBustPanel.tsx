import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Info } from 'lucide-react';
import { useSettings } from '@/context/SettingsContext';
import { API_BASE_URL } from '@/lib/api';

interface BustFactor {
  name: string;
  contribution: number;
  direction: 'POSITIVE' | 'NEGATIVE';
}

interface ForecastBustSignal {
  signal: 'NORMAL' | 'ELEVATED' | 'INSUFFICIENT_DATA' | 'UNAVAILABLE';
  variable: string;
  lead_time_hours: number;
  bust_threshold?: number;
  historical_error_quantile: number;
  primary_factors: BustFactor[];
  regime_context?: string;
  status: string;
  provenance: string;
}

interface ForecastBustPanelProps {
  latitude: number;
  longitude: number;
  horizonHours: number;
  model: string;
  locationName: string;
}

export function ForecastBustPanel({ latitude, longitude, horizonHours, model, locationName }: ForecastBustPanelProps) {
  const { convertTempDelta, tempSymbol } = useSettings();
  const [data, setData] = useState<ForecastBustSignal | null>(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    let ignore = false;
    
    async function fetchData() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/bust/signal?latitude=${latitude}&longitude=${longitude}&lead_time_hours=${horizonHours}&model=${model}&location_name=${encodeURIComponent(locationName)}&variable=temperature_2m`);
        if (res.ok && !ignore) {
          const fetchedData = await res.json();
          setData(fetchedData);
        }
      } catch (err) {
        console.error("Failed to fetch forecast bust signal", err);
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    
    fetchData();
    return () => { ignore = true; };
  }, [latitude, longitude, horizonHours, model, locationName]);

  if (loading) {
    return (
      <div className="mt-3 p-3 bg-surface-raised rounded-md border border-border-subtle animate-pulse">
        <div className="text-[10px] uppercase font-bold tracking-wider text-text-secondary">Analyzing Bust Risk...</div>
      </div>
    );
  }

  if (!data || data.status === 'UNAVAILABLE' || data.signal === 'UNAVAILABLE') {
    return null;
  }

  const isElevated = data.signal === 'ELEVATED';
  const isNormal = data.signal === 'NORMAL';

  return (
    <div className={`mt-3 p-3 bg-surface-raised rounded-md border ${isElevated ? 'border-amber-500/50' : 'border-border-subtle'}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[10px] uppercase font-bold tracking-wider text-text-secondary flex items-center gap-1.5">
          Forecast-Bust Risk
          <span title={data.provenance}><Info className="h-3 w-3 text-slate-400 cursor-help" /></span>
        </h4>
        {isElevated && (
          <span className="text-[10px] font-bold text-amber-500 flex items-center bg-amber-500/10 px-1.5 py-0.5 rounded-sm border border-amber-500/20">
            <AlertCircle className="w-3 h-3 mr-1" />
            ELEVATED
          </span>
        )}
        {isNormal && (
          <span className="text-[10px] font-bold text-emerald-500 flex items-center bg-emerald-500/10 px-1.5 py-0.5 rounded-sm border border-emerald-500/20">
            <CheckCircle className="w-3 h-3 mr-1" />
            NORMAL
          </span>
        )}
      </div>
      
      <div className="space-y-3 font-mono text-[11px]">
        {data.status === 'INSUFFICIENT_DATA' || data.signal === 'INSUFFICIENT_DATA' ? (
          <div className="text-error text-[10px]">
            Insufficient data for bust detection.
          </div>
        ) : (
          <>
            {data.bust_threshold !== undefined && (
              <div className="text-[9px] text-text-tertiary">
                Historical error threshold ({data.historical_error_quantile * 100}th pctl): 
                <span className="font-bold text-white ml-1">
                  &gt; {convertTempDelta(data.bust_threshold).toFixed(2)} {tempSymbol}
                </span>
              </div>
            )}
            
            {data.primary_factors.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="text-[9px] uppercase tracking-wider text-text-tertiary mb-1">
                  Primary Factors
                </div>
                {data.primary_factors.map((factor, i) => (
                  <div key={i} className="flex justify-between items-center text-[10px]">
                    <span className="text-text-secondary">{factor.name.replace(/_/g, ' ')}</span>
                    <span className={factor.direction === 'POSITIVE' ? 'text-amber-400' : 'text-emerald-400'}>
                      {factor.direction === 'POSITIVE' ? '+' : '-'}{factor.contribution.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {data.regime_context && (
              <div className="mt-1 bg-background border border-border-subtle px-2 py-1 rounded-sm text-[9px] text-ensemble">
                {data.regime_context}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
