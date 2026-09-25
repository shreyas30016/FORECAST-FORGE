"use client";

import React, { createContext, useContext, useState, useCallback, useMemo, ReactNode } from "react";
import { useLocation } from "./LocationContext";

export interface NormalizedCopilotContext {
  page?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  variable?: string;
  lead_time_hours?: number;
  valid_time?: string;
  run_time?: string;
  trace_id?: string;
  replay_id?: string;
  replay_status?: string;
  provenance_status?: string;
  forecast_value?: number;
  realized_value?: number;
  selected_model?: string;
}

interface CopilotContextType {
  context: NormalizedCopilotContext;
  setCopilotContext: (ctx: Partial<NormalizedCopilotContext>) => void;
  resetCopilotContext: () => void;
}

const CopilotContext = createContext<CopilotContextType | undefined>(undefined);

export function CopilotProvider({ children }: { children: ReactNode }) {
  const { location, activeForecast } = useLocation();
  const [pageContext, setPageContext] = useState<Partial<NormalizedCopilotContext>>({});

  const setCopilotContext = useCallback((ctx: Partial<NormalizedCopilotContext>) => {
    setPageContext((prev) => ({ ...prev, ...ctx }));
  }, []);

  const resetCopilotContext = useCallback(() => {
    setPageContext({});
  }, []);

  // Merge ambient location, activeForecast, and explicit pageContext
  const mergedContext = useMemo<NormalizedCopilotContext>(() => {
    return {
      location: pageContext.location ?? location?.name ?? "Mumbai",
      latitude: pageContext.latitude ?? location?.latitude ?? 19.076,
      longitude: pageContext.longitude ?? location?.longitude ?? 72.8777,
      variable: pageContext.variable ?? activeForecast?.variable ?? "temperature_2m",
      lead_time_hours: pageContext.lead_time_hours ?? activeForecast?.lead_time_hours,
      valid_time: pageContext.valid_time ?? activeForecast?.valid_time,
      trace_id: pageContext.trace_id ?? activeForecast?.trace_id,
      ...pageContext,
    };
  }, [location, activeForecast, pageContext]);

  return (
    <CopilotContext.Provider
      value={{
        context: mergedContext,
        setCopilotContext,
        resetCopilotContext,
      }}
    >
      {children}
    </CopilotContext.Provider>
  );
}

export function useCopilot() {
  const ctx = useContext(CopilotContext);
  if (!ctx) {
    throw new Error("useCopilot must be used within a CopilotProvider");
  }
  return ctx;
}
