"use client";

import { useCopilot } from "@/context/CopilotContext";
import { ForecastCopilot } from "./ForecastCopilot";

export function GlobalCopilot() {
  const { context } = useCopilot();
  
  return <ForecastCopilot context={context} />;
}
