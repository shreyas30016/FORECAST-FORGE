import { 
  HealthResponse, 
  DataSourceHealth, 
  ModelInfo, 
  EnsembleResponse, 
  ForecastResponse,
  EvaluationResponse,
  HistoricalDataAPI,
  GridResponse,
  SpatialWeightGridResponse,
  SpatialLeadTimeWeightGridResponse,
  RegimeResponse
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData?.error?.message || `API request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  getHealth: () => fetchAPI<HealthResponse>("/health"),
  
  getDataSourcesHealth: () => fetchAPI<DataSourceHealth[]>("/data-sources/health"),
  
  getModels: () => fetchAPI<ModelInfo[]>("/models"),
  
  getForecast: (lat: number, lon: number, horizon: number = 72, name: string = "Unknown") => 
    fetchAPI<ForecastResponse>(`/forecast?latitude=${lat}&longitude=${lon}&horizon_hours=${horizon}&name=${encodeURIComponent(name)}`),
    
  getEnsemble: (lat: number, lon: number, variable: string = "temperature_2m", horizon: number = 72, name: string = "Unknown") => 
    fetchAPI<EnsembleResponse>(`/ensemble?latitude=${lat}&longitude=${lon}&horizon_hours=${horizon}&variable=${variable}&name=${encodeURIComponent(name)}`),
    
  getEvaluation: () => fetchAPI<EvaluationResponse>("/evaluation"),

  getHistorical: () => fetchAPI<HistoricalDataAPI>("/historical"),

  getGrid: (
    lat: number,
    lon: number,
    variable: string = "temperature_2m",
    model: string = "ecmwf_ifs025",
    validTime?: string,
    gridSize: number = 5,
    step: number = 0.25
  ) => {
    let url = `/forecast/grid?latitude=${lat}&longitude=${lon}&variable=${variable}&model=${model}&grid_size=${gridSize}&step=${step}`;
    if (validTime) {
      url += `&valid_time=${encodeURIComponent(validTime)}`;
    }
    return fetchAPI<GridResponse>(url);
  },
  
  getWeightsGrid: (
    lat: number,
    lon: number,
    variable: string = "temperature_2m",
    gridSize: number = 5,
    step: number = 0.25,
    leadTimeHours?: number
  ) => {
    let url = `/ensemble/weights/grid?latitude=${lat}&longitude=${lon}&variable=${variable}&grid_size=${gridSize}&step=${step}`;
    if (leadTimeHours !== undefined) {
      url += `&lead_time_hours=${leadTimeHours}`;
    }
    return fetchAPI<SpatialWeightGridResponse | SpatialLeadTimeWeightGridResponse>(url);
  },

  getRegimes: () => fetchAPI<RegimeResponse>("/evaluation/regimes"),
  
  getDecisionTrace: (lat: number, lon: number, validTime: string, leadTime: number, variable: string = "temperature_2m", traceId?: string, replayId?: string) => {
    if (traceId) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return fetchAPI<any>(`/decision-trace?trace_id=${encodeURIComponent(traceId)}`);
    }
    if (replayId) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return fetchAPI<any>(`/decision-trace?replay_id=${encodeURIComponent(replayId)}`);
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return fetchAPI<any>(`/decision-trace?latitude=${lat}&longitude=${lon}&valid_time=${encodeURIComponent(validTime)}&lead_time_hours=${leadTime}&variable=${variable}`);
  },
  
  getReplayTimeline: (run: string, lat: number | string, lon: number | string, variable: string = "temperature_2m") =>
    fetchAPI<Record<string, unknown>>(`/replay/timeline?run=${encodeURIComponent(run)}&latitude=${lat}&longitude=${lon}&variable=${variable}`),

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  postAgentChat: async (data: any) => {
    const res = await fetch(`${API_BASE_URL}/agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      throw new Error(`API Error: ${res.status}`);
    }
    return res.json();
  }
};
