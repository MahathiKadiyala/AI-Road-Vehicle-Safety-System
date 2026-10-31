import {
  HealthResponse,
  HealthState,
  Hazard,
  DamageDetectionResponse,
  DamageModelStatusResponse,
  VehicleAssessmentPayload,
  VehicleAssessmentResult,
  VehicleStandardsResponse,
  RiskModelStatus,
  RiskPredictionPayload,
  RiskPredictionResult,
  HazardDensitySummary,
  NearbyHospital,
  NearbyHospitalsResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const DEFAULT_REQUEST_TIMEOUT_MS = 8000;

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  retries?: number;
}

/**
 * Resilient fetch wrapper with explicit timeout cancellation and bounded retries
 * for safe, idempotent HTTP GET requests.
 */
export async function resilientFetch(url: string, options: RequestOptions = {}): Promise<Response> {
  const {
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    retries = 0,
    ...fetchOptions
  } = options;

  let lastError: any = null;
  const isIdempotent = !fetchOptions.method || fetchOptions.method.toUpperCase() === 'GET';
  const maxAttempts = isIdempotent ? Math.min(retries + 1, 2) : 1;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (err: any) {
      clearTimeout(timeoutId);
      lastError = err;
      const isTimeout = err?.name === 'AbortError';

      if (attempt < maxAttempts - 1 && isIdempotent) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        continue;
      }

      if (isTimeout) {
        throw new Error(`Request timed out after ${timeoutMs / 1000}s. Please check your network connection.`);
      }
      throw err;
    }
  }

  throw lastError || new Error('Network request failed.');
}

export function computeHealthState(health: HealthResponse | null, loading: boolean): HealthState {
  if (loading && !health) {
    return 'connecting';
  }
  if (!health) {
    return 'offline';
  }
  if (health.status === 'healthy') {
    return 'healthy';
  }
  if (health.database.connected && !health.database.postgis_enabled) {
    return 'degraded_postgis';
  }
  if (!health.database.connected && health.status !== 'offline') {
    return 'degraded_db';
  }
  if (health.status === 'offline') {
    return 'offline';
  }
  return 'degraded_db';
}

export async function fetchHealthStatus(): Promise<HealthResponse> {
  try {
    const response = await resilientFetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      timeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
      retries: 0,
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error: any) {
    return {
      status: 'offline',
      project_name: 'AI-Powered Road and Vehicle Safety System',
      version: '0.1.0',
      environment: 'development',
      database: {
        connected: false,
        database_url_configured: false,
        postgis_enabled: false,
        error: error.message || 'Cannot reach FastAPI backend server.',
        setup_guidance: 'Make sure FastAPI is running on port 8000 (uvicorn app.main:app --reload).'
      },
      timestamp: new Date().toISOString()
    };
  }
}

// ── Phase 2: Hazard Reporting API ──────────────────────────────────────────

export interface CreateHazardPayload {
  title: string;
  description?: string;
  hazard_type: string;
  severity: string;
  latitude: number;
  longitude: number;
  image?: File | null;
}

export interface HazardListParams {
  hazard_type?: string;
  severity?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

/**
 * Submit a new hazard report (multipart/form-data for image support).
 */
export async function createHazardReport(payload: CreateHazardPayload): Promise<Hazard> {
  const formData = new FormData();
  formData.append('title', payload.title);
  formData.append('hazard_type', payload.hazard_type);
  formData.append('severity', payload.severity);
  formData.append('latitude', String(payload.latitude));
  formData.append('longitude', String(payload.longitude));

  if (payload.description) {
    formData.append('description', payload.description);
  }

  if (payload.image) {
    formData.append('image', payload.image);
  }

  const response = await resilientFetch(`${API_BASE_URL}/api/v1/hazards`, {
    method: 'POST',
    body: formData,
    timeoutMs: 15000,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail;
    let message = `HTTP ${response.status}`;
    if (Array.isArray(detail)) {
      message = detail.join(' ');
    } else if (typeof detail === 'string') {
      message = detail;
    }
    throw new Error(message);
  }

  return await response.json();
}

/**
 * Fetch all hazard reports with optional filtering.
 */
export async function fetchHazardReports(params?: HazardListParams): Promise<Hazard[]> {
  const searchParams = new URLSearchParams();

  if (params?.hazard_type) searchParams.set('hazard_type', params.hazard_type);
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));

  const qs = searchParams.toString();
  const url = `${API_BASE_URL}/api/v1/hazards${qs ? `?${qs}` : ''}`;

  const response = await resilientFetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hazard reports: HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Fetch a single hazard report by ID.
 */
export async function fetchHazardById(id: string): Promise<Hazard> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/hazards/${id}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hazard report: HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Build a full URL for a hazard image path.
 */
export function getHazardImageUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl) return null;
  // If already absolute, return as-is
  if (imageUrl.startsWith('http')) return imageUrl;
  return `${API_BASE_URL}${imageUrl}`;
}

// ── Phase 3: Road-Damage AI Detection API ───────────────────────────────────

/**
 * Fetch operational status and availability of the Road Damage YOLO model.
 */
export async function fetchDamageModelStatus(): Promise<DamageModelStatusResponse> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/damage/status`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to query model status: HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Upload a road image for distress detection (cracks D00/D10/D20, potholes D40).
 */
export async function detectRoadDamage(
  file: File,
  confidenceThreshold: number = 0.25
): Promise<DamageDetectionResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('confidence_threshold', String(confidenceThreshold));

  const response = await resilientFetch(`${API_BASE_URL}/api/v1/damage/detect`, {
    method: 'POST',
    body: formData,
    timeoutMs: 30000,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail;

    if (response.status === 503) {
      const msg = typeof detail === 'object' && detail?.message ? detail.message : 'Road damage model is currently unavailable.';
      throw new Error(`Model Unavailable (503): ${msg}`);
    }

    let message = `Inference failed (HTTP ${response.status})`;
    if (typeof detail === 'string') {
      message = detail;
    } else if (typeof detail === 'object' && detail?.message) {
      message = detail.message;
    }
    throw new Error(message);
  }

  return await response.json();
}

// ── Phase 4: Vehicle Safety Assessment API ─────────────────────────────────

/**
 * Fetch verified statutory and technical vehicle safety standards registry.
 */
export async function fetchVehicleStandards(): Promise<VehicleStandardsResponse> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/vehicles/standards`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to load vehicle safety standards (HTTP ${response.status})`);
  }

  return await response.json();
}

/**
 * Submit vehicle parameters for deterministic safety and statutory compliance evaluation.
 */
export async function assessVehicle(
  payload: VehicleAssessmentPayload
): Promise<VehicleAssessmentResult> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/vehicles/assess`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
    timeoutMs: 12000,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail;

    let message = `Vehicle assessment failed (HTTP ${response.status})`;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((err: any) => `${err.loc?.slice(-1)[0]}: ${err.msg}`).join(', ');
    } else if (typeof detail === 'object' && detail?.message) {
      message = detail.message;
    }
    throw new Error(message);
  }

  return await response.json();
}

/**
 * Retrieve a previously persisted vehicle safety assessment by ID.
 */
export async function fetchVehicleAssessmentById(
  id: string
): Promise<VehicleAssessmentResult> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/vehicles/${id}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to load vehicle assessment ${id} (HTTP ${response.status})`);
  }

  return await response.json();
}


// ── Phase 5: Accident-Risk Prediction & Spatial Density API ────────────────

/**
 * Fetch real nearby hazard density from PostGIS spatial service.
 */
export async function fetchHazardDensity(
  latitude: number,
  longitude: number,
  radiusMeters: number = 1000
): Promise<HazardDensitySummary> {
  const params = new URLSearchParams({
    latitude: latitude.toString(),
    longitude: longitude.toString(),
    radius_meters: radiusMeters.toString(),
  });

  const response = await resilientFetch(`${API_BASE_URL}/api/v1/hazards/density?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch hazard density (HTTP ${response.status})`);
  }

  return await response.json();
}

/**
 * Query operational status and data provenance of the accident risk model.
 */
export async function fetchRiskModelStatus(): Promise<RiskModelStatus> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/risk/status`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to query risk model status: HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Request road-segment accident risk prediction.
 */
export async function predictAccidentRisk(
  payload: RiskPredictionPayload
): Promise<RiskPredictionResult> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/risk/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
    timeoutMs: 15000,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail;

    let message = `Risk prediction failed (HTTP ${response.status})`;
    if (typeof detail === 'string') {
      message = detail;
    } else if (typeof detail === 'object' && detail?.message) {
      message = detail.message;
    }
    throw new Error(message);
  }

  return await response.json();
}


// ── Phase 5.3: Hospital & Emergency Proximity API ─────────────────────────

/**
 * Fetch verified hospitals and trauma centers within a given radius.
 */
export async function fetchNearbyHospitals(
  latitude: number,
  longitude: number,
  radiusMeters: number = 10000,
  emergencyOnly: boolean = false,
  limit: number = 20
): Promise<NearbyHospitalsResponse> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    radius_meters: String(radiusMeters),
    emergency_only: String(emergencyOnly),
    limit: String(limit),
  });

  const response = await resilientFetch(`${API_BASE_URL}/api/v1/hospitals/nearby?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail || `HTTP ${response.status}`;
    throw new Error(`Failed to fetch nearby hospitals: ${detail}`);
  }

  return await response.json();
}

/**
 * Fetch a single hospital facility by its ID.
 */
export async function fetchHospitalById(id: string): Promise<NearbyHospital> {
  const response = await resilientFetch(`${API_BASE_URL}/api/v1/hospitals/${id}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    retries: 1,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hospital: HTTP ${response.status}`);
  }

  return await response.json();
}
