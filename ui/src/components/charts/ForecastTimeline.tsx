"use client";

import { useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  ComposedChart
} from "recharts";
import { TimelineRow } from "@/types/api";
import { useSettings } from "@/context/SettingsContext";

interface ForecastTimelineProps {
  data: TimelineRow[];
  variable?: string;
  unit?: string;
}

interface TooltipPayloadItem {
  name: string;
  value: number | string | null;
  color: string;
  dataKey: string;
  payload: TimelineRow;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  useUtc?: boolean;
  unit?: string;
}

// Custom tooltip declared outside render function to comply with React 19 rules
function CustomTimelineTooltip({ active, payload, useUtc, unit = "°C" }: CustomTooltipProps) {
  if (active && payload && payload.length > 0) {
    const rawTimestamp = payload[0]?.payload?.timestamp;
    if (!rawTimestamp) return null;

    const dateObj = parseISO(rawTimestamp);
    const timeFormatted = useUtc
      ? format(dateObj, "MMM dd · HH:mm 'UTC'")
      : format(dateObj, "MMM dd · HH:mm '(Local)'");

    return (
      <div className="bg-panel/95 border border-white/10 p-3 rounded-xl shadow-2xl font-mono text-xs z-50 backdrop-blur-md min-w-[180px]">
        <p className="text-white font-bold border-b border-white/10 pb-2 mb-2 text-[11px]">
          {timeFormatted}
        </p>
        <div className="space-y-1.5">
          {payload.map((p) => {
            if (p.dataKey === "spreadUpper" || p.dataKey === "spreadLower") return null;
            const isNull = p.value === null || p.value === undefined;
            const valDisplay = isNull ? "—" : `${Number(p.value).toFixed(2)}${unit}`;
            const isEnsemble = p.dataKey === "ensemble";

            return (
              <div key={p.dataKey} className="flex items-center justify-between gap-3">
                <span
                  className={`flex items-center gap-1.5 ${isEnsemble ? "font-bold" : ""}`}
                  style={{ color: p.color }}
                >
                  <span
                    className={`inline-block rounded-full shrink-0 ${isEnsemble ? "w-2.5 h-2.5" : "w-1.5 h-1.5"}`}
                    style={{ backgroundColor: p.color }}
                  />
                  {p.name}
                </span>
                <span className={`font-bold ${isNull ? "text-text-secondary" : "text-white"}`}>
                  {valDisplay}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  return null;
}

export function ForecastTimeline({ data, variable = "temperature_2m", unit }: ForecastTimelineProps) {
  const [useUtc, setUseUtc] = useState(true);
  const { convertTemp, convertWind, tempSymbol, windSymbol } = useSettings();

  const isTemp = variable === "temperature_2m";
  const isWind = variable === "wind_speed_10m";

  // Auto-resolve unit if not passed explicitly
  const resolvedUnit = useMemo(() => {
    if (unit) return unit;
    if (isTemp) return tempSymbol;
    if (isWind) return ` ${windSymbol}`;
    switch (variable) {
      case "relative_humidity_2m":
        return "%";
      case "precipitation":
        return " mm";
      default:
        return "";
    }
  }, [variable, unit, isTemp, isWind, tempSymbol, windSymbol]);

  const chartData = useMemo(() => {
    const convertVal = (v: unknown): number | null => {
      if (v === null || v === undefined || typeof v !== "number" || isNaN(v)) return null;
      if (isTemp) return parseFloat(convertTemp(v).toFixed(2));
      if (isWind) return parseFloat(convertWind(v).toFixed(2));
      return v;
    };

    return data.map((d) => {
      const dateObj = parseISO(d.timestamp);
      const timeLabel = useUtc ? format(dateObj, "HH:mm") : format(dateObj, "HH:mm");

      const ifs = convertVal(d.ecmwf_ifs025);
      const gfs = convertVal(d.gfs_seamless);
      const ens = convertVal(d.ensemble);

      const hasValidSpread = ens !== null && d.spread !== null && d.spread !== undefined;
      const spreadVal = hasValidSpread ? (isTemp ? convertTemp(Number(d.spread)) - convertTemp(0) : (isWind ? convertWind(Number(d.spread)) : Number(d.spread))) : null;
      const spreadUpper = hasValidSpread && ens !== null && spreadVal !== null ? ens + spreadVal * 1.96 : null;
      const spreadLower = hasValidSpread && ens !== null && spreadVal !== null ? ens - spreadVal * 1.96 : null;

      return {
        ...d,
        ecmwf_ifs025: ifs,
        gfs_seamless: gfs,
        ensemble: ens,
        timeLabel,
        spreadUpper,
        spreadLower,
      };
    });
  }, [data, useUtc, isTemp, isWind, convertTemp, convertWind]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[260px] text-text-secondary text-xs font-mono">
        NO FORECAST TELEMETRY LOADED
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-3">
      {/* Header: param + UTC toggle */}
      <div className="flex items-center justify-between text-xs font-mono text-text-muted">
        <span className="flex items-center gap-2">
          <span className="uppercase tracking-wide">{variable.replace(/_/g, " ")}</span>
          <span className="text-text-muted/60">[{resolvedUnit.trim()}]</span>
        </span>
        <div className="flex items-center gap-1 bg-background/60 border border-white/10 p-0.5 rounded-lg">
          <button
            type="button"
            onClick={() => setUseUtc(true)}
            className={`px-2.5 py-1 rounded-md transition-colors text-[10px] font-mono ${
              useUtc ? "bg-ensemble/20 text-ensemble font-bold" : "text-text-muted hover:text-white"
            }`}
            aria-pressed={useUtc}
          >
            UTC
          </button>
          <button
            type="button"
            onClick={() => setUseUtc(false)}
            className={`px-2.5 py-1 rounded-md transition-colors text-[10px] font-mono ${
              !useUtc ? "bg-ensemble/20 text-ensemble font-bold" : "text-text-muted hover:text-white"
            }`}
            aria-pressed={!useUtc}
          >
            Local
          </button>
        </div>
      </div>

      <div className="w-full" style={{ height: 420 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="2 8" stroke="rgba(255,255,255,0.04)" vertical={false} />
            
            <XAxis 
              dataKey="timestamp" 
              stroke="#64748B" 
              fontSize={11} 
              tickLine={false} 
              axisLine={false}
              tickMargin={10}
              minTickGap={60}
              tick={{ fill: "#64748B", fontFamily: "var(--font-mono)" }}
              tickFormatter={(val) => {
                const dateObj = parseISO(val);
                return useUtc ? format(dateObj, "dd MMM HH:mm") : format(dateObj, "dd MMM HH:mm");
              }}
            />
            
            <YAxis 
              stroke="#64748B" 
              fontSize={11} 
              tickLine={false} 
              axisLine={false}
              tickMargin={8}
              width={54}
              tick={{ fill: "#64748B", fontFamily: "var(--font-mono)" }}
              domain={["auto", "auto"]}
              tickFormatter={(val) => `${val}${resolvedUnit}`}
            />
            
            <Tooltip content={<CustomTimelineTooltip useUtc={useUtc} unit={resolvedUnit} />} />
            
            <Legend 
              wrapperStyle={{ fontSize: '11px', fontFamily: 'var(--font-mono)', paddingTop: '12px', color: '#94A3B8' }}
              iconType="circle"
              iconSize={8}
            />

            {/* Uncertainty Spread Band */}
            <Area 
              type="monotone" 
              dataKey="spreadUpper" 
              stroke="none" 
              fill="rgba(52, 211, 153, 0.08)" 
              name="Ensemble Spread"
              connectNulls={false}
            />
            <Area 
              type="monotone" 
              dataKey="spreadLower" 
              stroke="none" 
              fill="#06111F" 
              name="Spread Lower" 
              legendType="none"
              tooltipType="none"
              connectNulls={false}
            />

            {/* IFS Line */}
            <Line 
              type="monotone" 
              dataKey="ecmwf_ifs025" 
              name="IFS (ECMWF)" 
              stroke="var(--color-ifs)" 
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 2"
              connectNulls={false} 
            />

            {/* GFS Line */}
            <Line 
              type="monotone" 
              dataKey="gfs_seamless" 
              name="GFS (NOAA)" 
              stroke="var(--color-gfs)" 
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 2"
              connectNulls={false} 
            />

            {/* AIFS Line — explicitly connectNulls=false, gaps preserved */}
            <Line 
              type="monotone" 
              dataKey="ecmwf_aifs025" 
              name="AIFS (ML)" 
              stroke="var(--color-aifs)" 
              strokeWidth={1}
              dot={false}
              strokeDasharray="2 4"
              opacity={0.5}
              connectNulls={false} 
            />

            {/* Ensemble Blended Line — dominant */}
            <Line 
              type="monotone" 
              dataKey="ensemble" 
              name="Ensemble Forecast" 
              stroke="var(--color-ensemble)" 
              strokeWidth={4}
              dot={{ r: 0 }}
              activeDot={{ r: 5, stroke: "var(--color-ensemble)", strokeWidth: 2, fill: "#06111F" }}
              connectNulls={false} 
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
