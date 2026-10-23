import { HealthResponse } from '../types';

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
