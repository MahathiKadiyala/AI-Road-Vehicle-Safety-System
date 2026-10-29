export type UserRole = 'driver' | 'buyer' | 'ambulance' | 'authority';

export interface DatabaseHealth {
  connected: boolean;
  database_url_configured: boolean;
  postgis_enabled: boolean;
  postgis_version?: string | null;
  server_version?: string | null;
  error?: string | null;
  setup_guidance?: string | null;
}

export type HealthState = 'connecting' | 'healthy' | 'degraded_db' | 'degraded_postgis' | 'offline';

export interface HealthResponse {
  status: string;
  project_name: string;
  version: string;
  environment: string;
  database: DatabaseHealth;
  timestamp: string;
}

export type HazardType = 'pothole' | 'crack' | 'debris' | 'waterlogging' | 'obstacle' | 'other';
export type HazardSeverity = 'low' | 'medium' | 'high' | 'critical';
export type HazardStatus = 'reported' | 'verified' | 'in_progress' | 'resolved' | 'dismissed';

export interface Hazard {
  id: string;
  title: string;
  description?: string;
  hazard_type: HazardType;
  severity: HazardSeverity;
  latitude: number;
  longitude: number;
  image_path?: string;
  image_url?: string | null;
  source: string;
  status: HazardStatus;
  created_at: string;
  updated_at: string;
}

export interface Hospital {
  id: string;
  name: string;
  facility_type: string;
  latitude: number;
  longitude: number;
  address?: string;
  contact_phone?: string;
  has_emergency_service: boolean;
  total_beds_reference?: number;
  is_verified_facility: boolean;
  created_at: string;
}

// ── Phase 3: Road-Damage Detection Types ───────────────────────────────────

export interface BoundingBox {
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
  width: number;
  height: number;
  pixel_box?: [number, number, number, number] | null;
}

export interface DamageDetectionItem {
  class_id: number;
  class_code: 'D00' | 'D10' | 'D20' | 'D40' | string;
  class_name: string;
  confidence: number;
  box: BoundingBox;
  suggested_hazard_type: string;
  suggested_severity: string;
}

export interface DamageDetectionResponse {
  success: boolean;
  model_name: string;
  model_version?: string;
  device: string;
  detections_count: number;
  detections: DamageDetectionItem[];
  inference_time_ms: number;
  image_width: number;
  image_height: number;
  annotated_image_url?: string | null;
  disclaimer: string;
}

export interface DamageModelStatusResponse {
  available: boolean;
  model_name: string;
  model_path: string;
  weights_present: boolean;
  device: string;
  supported_classes: Record<string, string>;
  details?: string | null;
}

// ── Phase 4: Vehicle Safety Assessment Types ───────────────────────────────

export interface ParameterAuditItem {
  parameter: string;
  measured_value: string | number;
  status: 'compliant' | 'warning' | 'violation' | 'unverified';
  is_statutory: boolean;
  statutory_reference: string;
  finding: string;
  recommendation: string;
  deduction_applied: number;
}

export interface VehicleAssessmentPayload {
  make: string;
  model: string;
  year: number;
  odometer_km: number;
  vehicle_category?: string;
  brake_pad_thickness_mm?: number | null;
  tyre_tread_depth_mm?: number | null;
  service_records_count: number;
  past_accidents_count: number;
  puc_valid?: boolean | null;
  insurance_valid?: boolean | null;
  fitness_certificate_valid?: boolean | null;
  disclaimer_acknowledged: boolean;
}

export interface VehicleAssessmentResult extends VehicleAssessmentPayload {
  id: string;
  preliminary_score: number;
  risk_tier: 'Low' | 'Moderate' | 'High' | 'Critical';
  vehicle_category: string;
  critical_warnings: string[];
  statutory_violations: string[];
  advisory_warnings: string[];
  parameter_breakdown: ParameterAuditItem[];
  missing_unverified_attributes: string[];
  data_completeness: string;
  document_verification_source: string;
  disclaimer_text: string;
  legal_disclaimer_version: string;
  created_at: string;
}

export interface VehicleStandardsResponse {
  standards: Record<string, any>;
  disclaimer: string;
  version: string;
}

// ── Phase 5: Accident Risk Prediction Types ───────────────────────────────

export interface RiskModelStatus {
  available: boolean;
  status: 'MODEL_AVAILABLE' | 'MODEL_UNAVAILABLE' | 'TRAINING_DATA_UNAVAILABLE';
  model_version?: string | null;
  model_architecture: string;
  dataset_provenance: string;
  training_date?: string | null;
  evaluation_metrics?: Record<string, number> | null;
  details: string;
  features_expected: string[];
  missing_dependencies: string[];
}

export interface RiskPredictionPayload {
  latitude: number;
  longitude: number;
  road_classification: string;
  speed_limit_kmh: number;
  surface_condition: string;
  lighting_condition: string;
  weather_condition: string;
  search_radius_meters: number;
  vehicle_safety_score?: number | null;
}

export interface FeatureContributionItem {
  feature_name: string;
  feature_value: any;
  attribution_value: number;
  direction: 'increases_risk' | 'decreases_risk';
  description: string;
}

export interface RiskPredictionResult {
  prediction_id: string;
  status: 'success' | 'model_unavailable';
  risk_tier: 'Low' | 'Medium' | 'High' | 'Critical' | 'Unavailable';
  risk_score: number | null;
  risk_score_interpretation: string;
  model_version: string;
  corridor_coordinates: { latitude: number; longitude: number };
  spatial_hazard_density: Record<string, any>;
  features_used: Record<string, any>;
  feature_contributions: FeatureContributionItem[];
  actionable_recommendations: string[];
  disclaimer: string;
  evaluated_at: string;
}

export interface HazardDensitySummary {
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  area_sqkm: number;
  total_hazards: number;
  density_per_sqkm: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  critical_and_high_count: number;
  spatial_engine: string;
  hazards_with_missing_geometry_count: number;
  advisory_notes: string[];
}


// ── Phase 5.3: Hospital & Emergency Proximity Types ─────────────────────────

export interface NearbyHospital {
  id: string;
  name: string;
  facility_type: string;
  latitude: number;
  longitude: number;
  straight_line_distance_meters: number;
  straight_line_distance_km: number;
  address?: string | null;
  contact_phone?: string | null;
  has_emergency_service: boolean;
  total_beds_reference?: number | null;
  is_verified_facility: boolean;
  data_source: string;
}

export interface NearbyHospitalsResponse {
  center_latitude: number;
  center_longitude: number;
  search_radius_meters: number;
  total_found: number;
  spatial_engine: string;
  emergency_only_filter: boolean;
  hospitals: NearbyHospital[];
  advisory_notes: string[];
  emergency_helplines_india: Record<string, string>;
  disclaimer: string;
}
