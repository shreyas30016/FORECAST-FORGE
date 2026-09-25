"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/shared/Card";
import { Server, CheckCircle2, AlertCircle, AlertTriangle, XCircle, Clock } from "lucide-react";
import { ProviderResultAPI, ModelForecastAPI } from "@/types/api";

interface ProviderHealthProps {
  providers?: Record<string, ProviderResultAPI>;
  models?: Record<string, ModelForecastAPI>;
  className?: string;
}

interface ModelMeta {
  id: string;
  name: string;
  provider: string;
  type: string;
  resolution: string;
  colorVar: string;
}

const KNOWN_MODELS: Record<string, ModelMeta> = {
  ecmwf_ifs025: {
    id: "ecmwf_ifs025",
    name: "ECMWF IFS",
    provider: "European Centre for Medium-Range Weather Forecasts",
    type: "NWP Physics Model",
    resolution: "0.25° (~28 km)",
    colorVar: "var(--color-ifs)",
  },
  gfs_seamless: {
    id: "gfs_seamless",
    name: "NOAA GFS",
    provider: "National Oceanic and Atmospheric Administration",
    type: "NWP Physics Model",
    resolution: "0.25° (~28 km)",
    colorVar: "var(--color-gfs)",
  },
  ecmwf_aifs025: {
    id: "ecmwf_aifs025",
    name: "ECMWF AIFS · AI Model",
    provider: "European Centre for Medium-Range Weather Forecasts",
    type: "Data-Driven AI Model",
    resolution: "0.25° (~28 km)",
    colorVar: "var(--color-aifs)",
  },
};

/**
 * Derive a canonical ProviderStatus string from already-loaded forecast data.
 *
 * Priority: Use the explicit status string from the API response when present.
 * Otherwise, infer from valid record count so we never fabricate a status.
 *
 * Status definitions:
 *   AVAILABLE     — provider responded with valid forecast values
 *   DEGRADED      — provider responded but only some records have valid values
 *   NO_VALID_DATA — provider responded (HTTP 200) but zero usable values exist
 *   UNAVAILABLE   — network error, timeout, or HTTP error response
 *   STALE         — only cached data available past freshness threshold
 */
function deriveStatus(
  providerData: ProviderResultAPI | undefined,
  modelData: ModelForecastAPI | undefined
): {
  status: string;
  validCount: number;
  totalCount: number;
  reason: string | null;
} {
  // If we have no data at all (props not passed yet / still loading)
  if (!providerData && !modelData) {
    return { status: "LOADING", validCount: 0, totalCount: 0, reason: null };
  }

  // Prefer the raw provider record set because it has per-record granularity
  if (providerData) {
    const rawStatus = providerData.status || "UNKNOWN";
    const records = providerData.records || [];
    const validCount = records.filter((r) => r.temperature_2m !== null && r.temperature_2m !== undefined).length;
    const totalCount = records.length;

    // If the backend already gave us an authoritative status, trust it
    if (rawStatus !== "UNKNOWN") {
      return { status: rawStatus, validCount, totalCount, reason: null };
    }

    // Infer from record counts when status is unknown
    if (totalCount === 0) return { status: "NO_VALID_DATA", validCount: 0, totalCount: 0, reason: "Provider returned no records for this context." };
    if (validCount === 0) return { status: "NO_VALID_DATA", validCount: 0, totalCount, reason: "Provider responded but all values are null." };
    if (validCount === totalCount) return { status: "AVAILABLE", validCount, totalCount, reason: null };
    return { status: "DEGRADED", validCount, totalCount, reason: `${totalCount - validCount} of ${totalCount} records missing values.` };
  }

  // Fall back to model-level status from ensemble response
  if (modelData) {
    const modelStatus = modelData.status || "UNKNOWN";
    const isAvail = modelStatus.includes("AVAILABLE") && !modelStatus.includes("UN") && !modelStatus.includes("NO_");
    return {
      status: isAvail ? "AVAILABLE" : modelStatus,
      validCount: isAvail ? 1 : 0,
      totalCount: 1,
      reason: null,
    };
  }

  return { status: "UNKNOWN", validCount: 0, totalCount: 0, reason: null };
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "AVAILABLE":
      return <CheckCircle2 className="w-4 h-4 text-status-available" />;
    case "DEGRADED":
      return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    case "STALE":
      return <Clock className="w-4 h-4 text-amber-400" />;
    case "NO_VALID_DATA":
      return <AlertCircle className="w-4 h-4 text-amber-400" />;
    case "UNAVAILABLE":
    case "ERROR":
    case "RATE_LIMITED":
      return <XCircle className="w-4 h-4 text-status-unavailable" />;
    default:
      return <AlertCircle className="w-4 h-4 text-text-muted" />;
  }
}

function StatusLabel({ status }: { status: string }) {
  const styles: Record<string, string> = {
    AVAILABLE: "text-status-available",
    DEGRADED: "text-amber-400",
    STALE: "text-amber-400",
    NO_VALID_DATA: "text-amber-400",
    UNAVAILABLE: "text-status-unavailable",
    ERROR: "text-status-unavailable",
    RATE_LIMITED: "text-status-unavailable",
    LOADING: "text-text-muted",
  };

  const labels: Record<string, string> = {
    NO_VALID_DATA: "NO VALID DATA",
    RATE_LIMITED: "RATE LIMITED",
    LOADING: "—",
  };

  return (
    <span className={`text-xs font-bold font-mono ${styles[status] ?? "text-text-muted"}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function ProviderHealth({ providers, models, className = "" }: ProviderHealthProps) {
  const modelKeys = ["ecmwf_ifs025", "gfs_seamless", "ecmwf_aifs025"];

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>
          <Server className="w-4 h-4 text-ensemble" /> Provider Health &amp; Data Availability
        </CardTitle>
      </CardHeader>

      <CardContent className="p-3 sm:p-4 space-y-3">
        {modelKeys.map((key) => {
          const meta = KNOWN_MODELS[key];
          const providerData = providers?.[key];
          const modelData = models?.[key];
          const { status, validCount, totalCount } = deriveStatus(providerData, modelData);

          const coverage =
            totalCount > 0 ? Math.round((validCount / totalCount) * 100) : 0;

          return (
            <div
              key={key}
              className="p-3 bg-background/50 border border-white/5 rounded-xl flex flex-col gap-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: meta.colorVar }}
                  />
                  <div>
                    <span className="font-bold text-white text-sm">{meta.name}</span>
                    <span className="text-xs text-text-muted block">{meta.type}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <StatusIcon status={status} />
                  <StatusLabel status={status} />
                </div>
              </div>

              {/* Record telemetry */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-white/5">
                <div>
                  <span className="text-text-muted block">Valid Records</span>
                  {status === "LOADING" ? (
                    <span className="text-text-muted">—</span>
                  ) : status === "AVAILABLE" ? (
                    <span className="text-status-available font-bold">
                      {totalCount > 0 ? `${validCount}/${totalCount}` : "—"}
                    </span>
                  ) : status === "DEGRADED" ? (
                    <span className="text-amber-400 font-bold">
                      {validCount}/{totalCount}
                    </span>
                  ) : (
                    <span className="text-status-unavailable font-bold">
                      {key === "ecmwf_aifs025" ? "0 usable records" : `${validCount}/${totalCount}`}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-text-muted block">Coverage</span>
                  {status === "LOADING" ? (
                    <span className="text-text-muted">—</span>
                  ) : status === "AVAILABLE" ? (
                    <span className="text-status-available font-bold">100%</span>
                  ) : status === "DEGRADED" ? (
                    <span className="text-amber-400 font-bold">{coverage}%</span>
                  ) : (
                    <span className="text-text-muted">
                      {key === "ecmwf_aifs025" ? "Excluded from ensemble" : "0%"}
                    </span>
                  )}
                </div>
              </div>

              {/* Context note for AIFS */}
              {key === "ecmwf_aifs025" && (
                <div className="text-[11px] text-text-muted border-t border-white/5 pt-2">
                  AIFS returned null values for this coordinate. Excluded from ensemble per null-safety protocol. No substitution applied.
                </div>
              )}

              {/* Explanation for other unavailable states */}
              {key !== "ecmwf_aifs025" && (status === "UNAVAILABLE" || status === "ERROR") && (
                <div className="flex items-start gap-1.5 text-[11px] text-status-unavailable pt-1 border-t border-white/5">
                  <XCircle className="w-3 h-3 mt-0.5 shrink-0" />
                  <span>Provider network error or HTTP failure. Not a data quality issue.</span>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
