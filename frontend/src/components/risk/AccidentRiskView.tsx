import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Sparkles,
  AlertTriangle,
  RotateCcw,
  MapPin,
  Activity,
  FileCode,
  Gauge,
  Ambulance,
} from 'lucide-react';
import {
  RiskModelStatus,
  HazardDensitySummary,
  RiskPredictionPayload,
} from '../../types';
import {
  fetchRiskModelStatus,
  fetchHazardDensity,
  predictAccidentRisk,
} from '../../services/api';

interface AccidentRiskViewProps {
  initialLat?: number;
  initialLon?: number;
  initialVehicleScore?: number | null;
  onNavigateToEmergency?: (lat: number, lon: number) => void;
  onNavigateToMap?: (lat: number, lon: number) => void;
}

export const AccidentRiskView: React.FC<AccidentRiskViewProps> = ({
  initialLat,
  initialLon,
  initialVehicleScore,
  onNavigateToEmergency,
  onNavigateToMap,
}) => {
  // State
  const [modelStatus, setModelStatus] = useState<RiskModelStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Form parameters
  const [latitude, setLatitude] = useState<number>(initialLat ?? 12.9716);
  const [longitude, setLongitude] = useState<number>(initialLon ?? 77.5946);
  const [roadClass, setRoadClass] = useState<string>('urban_arterial');
  const [speedLimit, setSpeedLimit] = useState<number>(50);
  const [surface, setSurface] = useState<string>('dry');
  const [lighting, setLighting] = useState<string>('daylight');
  const [weather, setWeather] = useState<string>('clear');
  const [radiusMeters, setRadiusMeters] = useState<number>(1000);
  const [vehicleSafetyScore, setVehicleSafetyScore] = useState<number | null>(initialVehicleScore ?? null);

  // Sync props when coordinates or vehicle score change
  useEffect(() => {
    if (initialLat !== undefined && initialLon !== undefined) {
      setLatitude(initialLat);
      setLongitude(initialLon);
    }
  }, [initialLat, initialLon]);

  useEffect(() => {
    if (initialVehicleScore !== undefined && initialVehicleScore !== null) {
      setVehicleSafetyScore(initialVehicleScore);
    }
  }, [initialVehicleScore]);

  // Spatial density probe state
  const [densityData, setDensityData] = useState<HazardDensitySummary | null>(null);
  const [loadingDensity, setLoadingDensity] = useState<boolean>(false);
  const [densityError, setDensityError] = useState<string | null>(null);

  // Prediction attempt state
  const [predicting, setPredicting] = useState<boolean>(false);
  const [predictError, setPredictError] = useState<string | null>(null);

  // Load model status on mount
  const loadStatus = async () => {
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const data = await fetchRiskModelStatus();
      setModelStatus(data);
    } catch (err: any) {
      setStatusError(err.message || 'Could not fetch risk model status.');
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  // Run live spatial hazard density query using Phase 5.1 PostGIS endpoint
  const handleQuerySpatialDensity = async () => {
    setLoadingDensity(true);
    setDensityError(null);
    try {
      const data = await fetchHazardDensity(latitude, longitude, radiusMeters);
      setDensityData(data);
    } catch (err: any) {
      setDensityError(err.message || 'Spatial density query failed.');
    } finally {
      setLoadingDensity(false);
    }
  };

  // Attempt prediction (triggers honest 503 while model is uncalibrated)
  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setPredicting(true);
    setPredictError(null);

    const payload: RiskPredictionPayload = {
      latitude,
      longitude,
      road_classification: roadClass,
      speed_limit_kmh: speedLimit,
      surface_condition: surface,
      lighting_condition: lighting,
      weather_condition: weather,
      search_radius_meters: radiusMeters,
      vehicle_safety_score: vehicleSafetyScore,
    };

    try {
      await predictAccidentRisk(payload);
    } catch (err: any) {
      setPredictError(err.message || 'Prediction request rejected by backend.');
    } finally {
      setPredicting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-mono tracking-wider text-indigo-700 font-semibold">
                Phase 5 Architecture
              </span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono font-medium">
                Accident Risk & Explainability (TreeSHAP)
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 mt-2 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-600" />
              Corridor Accident-Risk Intelligence
            </h1>
            <p className="text-xs text-slate-600 mt-1 max-w-2xl">
              Evaluates road-segment crash probability by synthesizing real PostGIS hazard density,
              corridor geometry, environmental hazards, and explainable feature attributions.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadStatus}
              disabled={loadingStatus}
              className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-600 hover:text-indigo-600 hover:border-indigo-300 font-medium flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${loadingStatus ? 'animate-spin' : ''}`} />
              Refresh Status
            </button>
          </div>
        </div>

        {/* Honest Model Status Diagnostic Banner */}
        <div className="mt-4 p-4 rounded-xl border bg-slate-50 border-slate-200">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-amber-100 text-amber-800 mt-0.5">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  Model State:
                </span>
                <span className="text-xs font-mono font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  {loadingStatus ? 'Checking...' : modelStatus?.status || 'TRAINING_DATA_UNAVAILABLE'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {modelStatus?.details ||
                  'Accident risk prediction model weights are not loaded. Machine learning inference requires authentic calibrated crash data.'}
              </p>
              {statusError && (
                <div className="text-xs text-rose-600 mt-1 font-mono">
                  Notice: {statusError}
                </div>
              )}
              <div className="pt-2 text-[11px] text-slate-500 flex flex-wrap items-center gap-x-4 gap-y-1">
                <span>
                  <strong>Architecture:</strong> {modelStatus?.model_architecture || 'XGBoost + TreeSHAP'}
                </span>
                <span>
                  <strong>Provenance:</strong> {modelStatus?.dataset_provenance || 'Awaiting verified records'}
                </span>
                <span>
                  <strong>Zero Fake Predictions Rule:</strong> Active
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Corridor Form (Left) & Live Spatial Density / Pipeline Spec (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Corridor Parameter Input Form (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="border-b border-slate-100 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-sky-600" />
                Corridor Parameter Specifications
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Configure road segment attributes to probe hazard density and test prediction pipeline.
              </p>
            </div>

            {/* Quick Corridor Presets */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] text-slate-400 font-medium">Presets:</span>
              <button
                type="button"
                onClick={() => { setLatitude(12.9716); setLongitude(77.5946); }}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium cursor-pointer transition-colors"
              >
                Central
              </button>
              <button
                type="button"
                onClick={() => { setLatitude(12.9345); setLongitude(77.6265); }}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium cursor-pointer transition-colors"
              >
                Koramangala
              </button>
              <button
                type="button"
                onClick={() => { setLatitude(12.9996); setLongitude(77.5710); }}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium cursor-pointer transition-colors"
              >
                Malleshwaram
              </button>
            </div>
          </div>

          <form onSubmit={handlePredict} className="space-y-4">
            {/* Coordinates */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Latitude
                </label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value) || 0)}
                  className="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Longitude
                </label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value) || 0)}
                  className="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  required
                />
              </div>
            </div>

            {/* Road Classification & Speed Limit */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Road Category
                </label>
                <select
                  value={roadClass}
                  onChange={(e) => setRoadClass(e.target.value)}
                  className="w-full text-xs px-2.5 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="urban_arterial">Urban Arterial</option>
                  <option value="national_highway">National Highway</option>
                  <option value="state_highway">State Highway</option>
                  <option value="major_district_road">Major District Road</option>
                  <option value="rural_road">Rural Road</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Speed Limit (km/h)
                </label>
                <input
                  type="number"
                  min="20"
                  max="140"
                  value={speedLimit}
                  onChange={(e) => setSpeedLimit(parseInt(e.target.value) || 50)}
                  className="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Environmental Conditions */}
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-[10px] font-semibold text-slate-700 mb-1">
                  Surface
                </label>
                <select
                  value={surface}
                  onChange={(e) => setSurface(e.target.value)}
                  className="w-full text-[11px] px-2 py-1.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="dry">Dry</option>
                  <option value="wet">Wet</option>
                  <option value="waterlogged">Waterlogged</option>
                  <option value="unpaved">Unpaved</option>
                  <option value="loose_gravel">Gravel</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-slate-700 mb-1">
                  Lighting
                </label>
                <select
                  value={lighting}
                  onChange={(e) => setLighting(e.target.value)}
                  className="w-full text-[11px] px-2 py-1.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="daylight">Daylight</option>
                  <option value="dawn_dusk">Dawn/Dusk</option>
                  <option value="night_lit">Night (Lit)</option>
                  <option value="night_unlit">Night (Unlit)</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-slate-700 mb-1">
                  Weather
                </label>
                <select
                  value={weather}
                  onChange={(e) => setWeather(e.target.value)}
                  className="w-full text-[11px] px-2 py-1.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="clear">Clear</option>
                  <option value="rain">Rain</option>
                  <option value="fog">Fog</option>
                  <option value="haze">Haze</option>
                  <option value="heavy_wind">Wind</option>
                </select>
              </div>
            </div>

            {/* Radius for PostGIS Density */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-[11px] font-semibold text-slate-700">
                  Spatial Density Radius
                </label>
                <span className="text-[11px] font-mono font-medium text-sky-700">
                  {radiusMeters} m ({ (radiusMeters / 1000).toFixed(1) } km)
                </span>
              </div>
              <input
                type="range"
                min="100"
                max="5000"
                step="100"
                value={radiusMeters}
                onChange={(e) => setRadiusMeters(parseInt(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>

            {/* Vehicle Mechanical Safety Profile (Phase 4 Integration) */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/90 space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5 text-sky-600" />
                  Vehicle Safety Profile (Phase 4)
                </label>
                <span className="text-[10px] font-mono font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                  {vehicleSafetyScore !== null ? `${vehicleSafetyScore.toFixed(1)} / 100` : 'Default Baseline'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  placeholder="Optional score from Vehicle Assessment"
                  value={vehicleSafetyScore !== null ? vehicleSafetyScore : ''}
                  onChange={(e) => setVehicleSafetyScore(e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-full text-xs font-mono px-3 py-1.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                />
                {vehicleSafetyScore !== null && (
                  <button
                    type="button"
                    onClick={() => setVehicleSafetyScore(null)}
                    className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded-lg bg-white cursor-pointer"
                    title="Clear vehicle score"
                  >
                    Reset
                  </button>
                )}
              </div>
              <p className="text-[10px] text-slate-500">
                Integrates tyre wear and brake pad health from the Vehicle Safety module into risk evaluation.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="pt-2 flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={handleQuerySpatialDensity}
                disabled={loadingDensity}
                className="flex-1 px-3 py-2 rounded-xl border border-sky-200 bg-sky-50 hover:bg-sky-100 text-sky-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Activity className={`w-3.5 h-3.5 text-sky-600 ${loadingDensity ? 'animate-spin' : ''}`} />
                Probe Hazard Density
              </button>

              <button
                type="submit"
                disabled={predicting}
                className="flex-1 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm transition-colors cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                {predicting ? 'Evaluating...' : 'Request Prediction'}
              </button>
            </div>

            {/* Cross-Workflow Navigation Actions */}
            {(onNavigateToEmergency || onNavigateToMap) && (
              <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row gap-2">
                {onNavigateToMap && (
                  <button
                    type="button"
                    onClick={() => onNavigateToMap(latitude, longitude)}
                    className="flex-1 px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <MapPin className="w-3.5 h-3.5 text-sky-600" />
                    <span>View on Map</span>
                  </button>
                )}
                {onNavigateToEmergency && (
                  <button
                    type="button"
                    onClick={() => onNavigateToEmergency(latitude, longitude)}
                    className="flex-1 px-3 py-2 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Ambulance className="w-3.5 h-3.5 text-rose-600" />
                    <span>Locate Hospitals</span>
                  </button>
                )}
              </div>
            )}

            {/* Prediction Error Alert */}
            {predictError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  Inference Guard Active
                </div>
                <p className="text-[11px] text-rose-700 leading-relaxed">
                  {predictError}
                </p>
                <p className="text-[10px] text-rose-500 italic">
                  Note: The system rejects producing arbitrary numbers when genuine model weights are not loaded.
                </p>
              </div>
            )}
          </form>
        </div>

        {/* Right Column: Live Spatial Density & Dataset Pipeline Spec (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Phase 5.1 Real Hazard Density Output */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-600" />
                  Live Spatial Hazard Density Probe
                </h3>
                <p className="text-[11px] text-slate-500">
                  Real PostGIS / Haversine spatial aggregation from Phase 5.1 engine.
                </p>
              </div>
              {densityData && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Engine: {densityData.spatial_engine}
                </span>
              )}
            </div>

            {densityError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
                Spatial query failed: {densityError}
              </div>
            )}

            {densityData ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                    <div className="text-[10px] text-slate-500 uppercase font-mono">Nearby Hazards</div>
                    <div className="text-xl font-bold text-slate-900 mt-1 font-mono">
                      {densityData.total_hazards}
                    </div>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                    <div className="text-[10px] text-slate-500 uppercase font-mono">Hazard Density</div>
                    <div className="text-xl font-bold text-indigo-700 mt-1 font-mono">
                      {densityData.density_per_sqkm}
                      <span className="text-[10px] text-slate-500 font-sans ml-1">/ km²</span>
                    </div>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                    <div className="text-[10px] text-slate-500 uppercase font-mono">Critical / High</div>
                    <div className="text-xl font-bold text-rose-700 mt-1 font-mono">
                      {densityData.critical_and_high_count}
                    </div>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                    <div className="text-[10px] text-slate-500 uppercase font-mono">Search Area</div>
                    <div className="text-xl font-bold text-slate-800 mt-1 font-mono">
                      {densityData.area_sqkm}
                      <span className="text-[10px] text-slate-500 font-sans ml-1">km²</span>
                    </div>
                  </div>
                </div>

                {/* Breakdown by Type & Severity */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-50/60 rounded-xl border border-slate-200/80">
                    <div className="font-semibold text-slate-700 mb-2">Breakdown by Type:</div>
                    {Object.keys(densityData.by_type).length > 0 ? (
                      <div className="space-y-1 font-mono text-[11px]">
                        {Object.entries(densityData.by_type).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-slate-600">
                            <span className="capitalize">{k}:</span>
                            <span className="font-bold text-slate-900">{v}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">No hazards in radius</span>
                    )}
                  </div>

                  <div className="p-3 bg-slate-50/60 rounded-xl border border-slate-200/80">
                    <div className="font-semibold text-slate-700 mb-2">Breakdown by Severity:</div>
                    {Object.keys(densityData.by_severity).length > 0 ? (
                      <div className="space-y-1 font-mono text-[11px]">
                        {Object.entries(densityData.by_severity).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-slate-600">
                            <span className="capitalize">{k}:</span>
                            <span className="font-bold text-slate-900">{v}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">No hazards in radius</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center border border-dashed border-slate-200 rounded-xl text-slate-500 text-xs space-y-1">
                <MapPin className="w-6 h-6 text-slate-400 mx-auto" />
                <p>Click "Probe Hazard Density" to query real stored road hazards within {radiusMeters}m.</p>
              </div>
            )}
          </div>

          {/* Dataset Ingestion & Validation Specification Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-indigo-600" />
                ML Pipeline Data Specification
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                Phase 5.2 Schema
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              To train a genuine, non-synthetic XGBoost model, the pipeline requires historical corridor
              observations with confirmed collision outcomes.
            </p>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] text-slate-700 space-y-1">
              <div><strong>Target Label:</strong> target_high_accident_risk (binary 0 or 1)</div>
              <div><strong>Prediction Unit:</strong> Road corridor segment within specified time window</div>
              <div><strong>Leakage Safeguards:</strong> Location-aware & time-based holdout splitting</div>
              <div><strong>Explainability Engine:</strong> TreeSHAP (direction, attribution, base value)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
