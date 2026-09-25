export interface APIErrorDetails {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface APIErrorResponse {
  error: APIErrorDetails;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ProbabilisticForecast {
  model: string;
  variable: string;
  valid_time: string;
  latitude: number;
  longitude: number;
  lead_time_hours: number | null;
  member_count: number;
  valid_member_count: number;
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  mean: number | null;
  median: number | null;
  spread: number | null;
  status: string;
  provenance: string;
}

export interface EventProbabilityResult {
  variable: string;
  operator: string;
  threshold: number;
  probability: number | null;
  valid_member_count: number;
  status: string;
}


export interface DataSourceHealth {
  provider: string;
  model: string;
  status: string;
  last_checked: string | null;
  reason: string | null;
}

export interface ModelInfo {
  name: string;
  provider: string;
  status: string;
  capabilities: string[];
  last_checked: string | null;
  available_variables: string[];
  supported_forecast_horizon_hours: number;
  reason: string | null;
}

export interface LocationAPI {
  name: string | null;
  latitude: number;
  longitude: number;
}

export interface ModelForecastAPI {
  status: string;
  forecast: number | null;
  weight: number;
}

export interface EnsembleMetaAPI {
  forecast: number | null;
  method: string;
  uncertainty: number | null;
  data_quality: string;
}

export interface EnsembleExplanationAPI {
  primary_contributor?: string;
  dropped_models?: string[];
  reasoning?: string;
  [key: string]: unknown;
}

export interface EnsembleResponse {
  location: LocationAPI;
  retrieval_timestamp: string;
  valid_time: string;
  variable: string;
  models: Record<string, ModelForecastAPI>;
  ensemble: EnsembleMetaAPI;
  explanation: EnsembleExplanationAPI | null;
}

export interface ForecastPointAPI {
  timestamp: string;
  temperature_2m: number | null;
  relative_humidity_2m: number | null;
  precipitation: number | null;
  wind_speed_10m: number | null;
  cloud_cover: number | null;
}

export interface ProviderResultAPI {
  model: string;
  status: string;
  records: ForecastPointAPI[];
}

export interface ForecastResponse {
  location: LocationAPI;
  retrieval_timestamp: string;
  providers: Record<string, ProviderResultAPI>;
}

export interface ModelSkillRecord {
  model: string;
  variable: string;
  lead_time_hours: number | null;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  reliability_score?: number | null;
  weight?: number | null;
  sample_count: number;
  evaluation_period: string;
  reference_source: string;
  status: string;
}

export interface EvaluationResponse {
  lead_time_available: boolean;
  lead_time_notice: string | null;
  evaluations: ModelSkillRecord[];
}

export interface HistoricalDataAPI {
  location: LocationAPI;
  variable: string;
  data: Record<string, unknown>[];
}

export interface TimelineRow {
  timestamp: string;
  timeLabel?: string;
  ecmwf_ifs025?: number | null;
  gfs_seamless?: number | null;
  ecmwf_aifs025?: number | null;
  ensemble?: number | null;
  spread?: number | null;
  spreadUpper?: number | null;
  spreadLower?: number | null;
  [key: string]: string | number | null | undefined;
}

export interface GridCellAPI {
  latitude: number;
  longitude: number;
  value: number | null;
  wind_direction?: number | null;
  wind_speed?: number | null;
  variable: string;
  unit: string;
  model: string;
  valid_time: string;
  source: string;
  status: string;
  bounds: [[number, number], [number, number]];
  ensemble_value?: number | null;
  model_spread?: number | null;
  pairwise_difference?: number | null;
  weights_applied?: Record<string, number> | null;
  models_included?: string[] | null;
  models_excluded?: string[] | null;
  contributing_values?: Record<string, number | null> | null;
  explanation?: string | null;
}

export interface SpatialWeightRecord {
  latitude: number;
  longitude: number;
  bounds: [[number, number], [number, number]];
  variable: string;
  model: string;
  weight: number;
  historical_metric: number | null;
  metric_name: string;
  sample_count: number;
  evaluation_period: string;
  reference_source: string;
  status: string;
  coverage_type: string;
}

export interface SpatialWeightGridResponse {
  center_latitude: number;
  center_longitude: number;
  variable: string;
  grid_size: number;
  step: number;
  cells: SpatialWeightRecord[];
  coverage_disclosure: string;
  status: string;
}

export interface SpatialLeadTimeWeightRecord {
  latitude: number;
  longitude: number;
  bounds: [[number, number], [number, number]];
  variable: string;
  model: string;
  lead_time_hours: number;
  weight: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  sample_count: number;
  evaluation_period: string;
  evaluation_mode: string;
  causal_cutoff: string | null;
  reference_source: string;
  lead_time_semantics: string;
  provenance_source: string | null;
  status: string;
}

export interface SpatialLeadTimeWeightGridResponse {
  center_latitude: number;
  center_longitude: number;
  variable: string;
  lead_time_hours: number;
  grid_size: number;
  step: number;
  evaluation_mode: string;
  causal_cutoff: string | null;
  cells: SpatialLeadTimeWeightRecord[];
  coverage_disclosure: string;
  status: string;
}

export interface GridDisagreementCellAPI {
  latitude: number;
  longitude: number;
  disagreement: number | null;
  min_value: number | null;
  max_value: number | null;
  models_included: string[];
  variable: string;
  unit: string;
  valid_time: string;
  bounds: [[number, number], [number, number]];
}

export interface EnsembleSummaryModelInfo {
  name: string;
  type: string;
  value: number | null;
  weight: number;
  status: string;
  reason?: string;
  skill?: {
    mae?: number | null;
    rmse?: number | null;
    bias?: number | null;
    samples?: number;
  };
}

export interface EnsembleSummaryAPI {
  valid_time: string;
  variable: string;
  unit: string;
  ensemble_value: number | null;
  model_spread: number | null;
  pairwise_difference: number | null;
  weights_applied: Record<string, number>;
  models: Record<string, EnsembleSummaryModelInfo>;
  data_quality: string;
  explanation: string;
  method: string;
  high_spread_threshold: number;
}

export interface GridResponse {
  center_latitude: number;
  center_longitude: number;
  variable: string;
  unit: string;
  model: string;
  valid_time: string;
  available_valid_times: string[];
  step: number;
  grid_size: number;
  points_count: number;
  cells: GridCellAPI[];
  disagreement_cells?: GridDisagreementCellAPI[] | null;
  status: string;
  provenance_notice: string;
  spatial_uncertainty_available: boolean;
  spatial_uncertainty_notice?: string | null;
  ensemble_summary?: EnsembleSummaryAPI | null;
}

export interface RegimeDefinition {
  regime_id: number;
  description: string;
  feature_summary: {
    temperature_2m: number | null;
    relative_humidity_2m: number | null;
    precipitation: number | null;
    wind_speed_10m: number | null;
    cloud_cover: number | null;
  };
  sample_count: number;
  training_period: string;
  model_version: string;
  provenance: string;
}

export interface RegimeResponse {
  status: string;
  model_version?: string;
  regimes: RegimeDefinition[];
  message?: string;
}
