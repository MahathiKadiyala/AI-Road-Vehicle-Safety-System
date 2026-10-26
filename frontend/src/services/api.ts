import { HealthResponse, Hazard } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function fetchHealthStatus(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
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

  const response = await fetch(`${API_BASE_URL}/api/v1/hazards`, {
    method: 'POST',
    body: formData,
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

  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
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
  const response = await fetch(`${API_BASE_URL}/api/v1/hazards/${id}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
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
