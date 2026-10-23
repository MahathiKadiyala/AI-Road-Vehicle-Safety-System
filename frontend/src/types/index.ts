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
