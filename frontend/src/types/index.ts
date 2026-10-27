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
