"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/shared/Card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EnsembleResponse } from "@/types/api";
import { Layers, ShieldAlert, Cpu } from "lucide-react";
import { useSettings } from "@/context/SettingsContext";

interface EnsembleInsightsProps {
  ensemble: EnsembleResponse;
  className?: string;
}

export function EnsembleInsights({ ensemble, className = "" }: EnsembleInsightsProps) {
  const { convertTemp, tempSymbol } = useSettings();
  const { models, ensemble: meta, explanation } = ensemble;

  const colors: Record<string, string> = {
    ecmwf_ifs025: "var(--color-ifs)",
    gfs_seamless: "var(--color-gfs)",
    ecmwf_aifs025: "var(--color-aifs)",
  };

  const labels: Record<string, string> = {
    ecmwf_ifs025: "ECMWF IFS",
    gfs_seamless: "NOAA GFS",
    ecmwf_aifs025: "ECMWF AIFS · AI Model",
  };

  return (
    <Card className={`h-full ${className}`}>
      <CardHeader>
        <CardTitle>
          <Layers className="w-4 h-4 text-ensemble" /> Ensemble Weight Distribution
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-secondary font-mono">METHOD:</span>
          <span className="text-[11px] font-mono font-bold text-white bg-background px-2 py-0.5 border border-border-subtle rounded-sm">
            {meta.method}
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-3 sm:p-4 flex flex-col gap-4 font-mono text-xs">
        {/* Model Contributions List */}
        <div className="space-y-3">
          {Object.entries(models).map(([modelId, data]) => {
            const wPercent = data.weight * 100;
            const isAvail = data.status.includes("AVAILABLE") && !data.status.includes("UN");
            const forecastDisplay = isAvail && data.forecast !== null ? `${convertTemp(data.forecast).toFixed(1)}${tempSymbol}` : "—";

            return (
              <div key={modelId} className="flex flex-col gap-1.5 p-2 bg-background/40 border border-border-subtle/70 rounded-sm">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                      style={{ backgroundColor: colors[modelId] || "#94A3B8" }}
                    />
                    <span className="text-white font-bold">{labels[modelId] || modelId}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-text-secondary text-[11px]">
                      Value: <strong className="text-white">{forecastDisplay}</strong>
                    </span>
                    <StatusBadge status={data.status} />
                    <span className="w-10 text-right font-bold text-white">
                      {isAvail ? `${wPercent.toFixed(0)}%` : "0%"}
                    </span>
                  </div>
                </div>

                {/* Contribution weight progress bar */}
                <div className="w-full bg-background h-1.5 rounded-full overflow-hidden border border-border-subtle">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: isAvail ? `${wPercent}%` : "0%",
                      backgroundColor: colors[modelId] || "#94A3B8",
                    }}
                  />
                </div>

                {!isAvail && (
                  <div className="text-[10px] text-status-unavailable flex items-center gap-1.5 mt-0.5">
                    <ShieldAlert className="w-3 h-3 shrink-0" />
                    <span>Provider returned no valid forecast values (Excluded from ensemble).</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Analytical Explanation Box */}
        {explanation && (
          <div className="mt-auto p-3 bg-panel-hover/50 border border-border-subtle rounded-sm text-xs space-y-2">
            <div className="flex items-center gap-1.5 text-text-secondary font-bold text-[11px] uppercase tracking-wider">
              <Cpu className="w-3.5 h-3.5 text-ensemble" /> Engine Synthesis Rationale
            </div>
            
            {explanation.reasoning && (
              <p className="text-text-primary text-[11px] leading-relaxed">
                {String(explanation.reasoning)}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-3 text-[10px] pt-2 border-t border-border-subtle text-text-secondary">
              {explanation.primary_contributor && (
                <div>
                  <span>PRIMARY: </span>
                  <strong className="text-ensemble">{String(explanation.primary_contributor)}</strong>
                </div>
              )}
              {Array.isArray(explanation.dropped_models) && explanation.dropped_models.length > 0 && (
                <div>
                  <span>DROPPED: </span>
                  <strong className="text-status-unavailable">{explanation.dropped_models.join(", ")}</strong>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
