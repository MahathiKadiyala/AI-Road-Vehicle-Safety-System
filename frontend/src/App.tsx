import React, { useState, useEffect, useCallback } from 'react';
import { UserRole, HealthResponse, Hazard, HazardType, HazardSeverity } from './types';
import { fetchHealthStatus, fetchHazardReports } from './services/api';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { DisclaimerBanner } from './components/common/DisclaimerBanner';
import { MapContainer } from './components/map/MapContainer';
import { HazardReportForm } from './components/hazards/HazardReportForm';
import { HazardReportList } from './components/hazards/HazardReportList';
import { DamageDetectionView } from './components/damage/DamageDetectionView';
import {
  Database,
  MapPin,
  Layers,
  Info,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';

export const App: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<UserRole>('driver');
  const [activeTab, setActiveTab] = useState<string>('map');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [selectedCoord, setSelectedCoord] = useState<{ lat: number; lon: number }>({
    lat: 12.9716,
    lon: 77.5946
  });

  // Phase 2: Hazard reporting state
  const [hazards, setHazards] = useState<Hazard[]>([]);
  const [loadingHazards, setLoadingHazards] = useState<boolean>(false);
  const [focusHazard, setFocusHazard] = useState<Hazard | null>(null);

  // Phase 3: AI Detection prefill state for handoff to citizen report form
  const [hazardPrefill, setHazardPrefill] = useState<{
    title: string;
    description: string;
    hazard_type: HazardType;
    severity: HazardSeverity;
    imageFile?: File;
  } | null>(null);

  const checkHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await fetchHealthStatus();
      setHealth(data);
    } catch (err) {
      console.warn('Health check request error:', err);
    } finally {
      setLoadingHealth(false);
    }
  };

  const loadHazards = useCallback(async () => {
    setLoadingHazards(true);
    try {
      const data = await fetchHazardReports({ limit: 100 });
      setHazards(data);
    } catch (err) {
      console.warn('Could not fetch hazard reports:', err);
    } finally {
      setLoadingHazards(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    loadHazards();
    const healthInterval = setInterval(checkHealth, 30000);
    const hazardInterval = setInterval(loadHazards, 15000);
    return () => {
      clearInterval(healthInterval);
      clearInterval(hazardInterval);
    };
  }, [loadHazards]);

  const handleSelectHazard = useCallback((hazard: Hazard) => {
    setFocusHazard(hazard);
    setSelectedCoord({ lat: hazard.latitude, lon: hazard.longitude });
    setTimeout(() => setFocusHazard(null), 2000);
  }, []);

  const handlePrefillHazard = (data: {
    hazard_type: string;
    severity: string;
    title: string;
    description: string;
    imageFile?: File;
  }) => {
    setHazardPrefill({
      hazard_type: data.hazard_type as HazardType,
      severity: data.severity as HazardSeverity,
      title: data.title,
      description: data.description,
      imageFile: data.imageFile,
    });
    setActiveTab('hazards');
    setTimeout(() => {
      window.scrollTo({ top: 600, behavior: 'smooth' });
    }, 100);
  };

  const roleDescriptions: Record<UserRole, { title: string; desc: string; phase: string }> = {
    driver: {
      title: 'Citizen Driver Experience',
      desc: 'Report potholes, cracks, and road obstacles with camera evidence, and inspect road distress with YOLO computer vision.',
      phase: 'Phase 2 & 3 Active'
    },
    buyer: {
      title: 'Used-Vehicle Buyer Experience',
      desc: 'Transparent tyre tread depth and brake pad condition assessment against CMVR Rule 95 legal standards.',
      phase: 'Phase 4 Planned'
    },
    ambulance: {
      title: 'Ambulance Emergency Support',
      desc: 'Advisory hazard-penalized route guidance and verified emergency trauma hospital proximity lookup.',
      phase: 'Phase 6 Planned'
    },
    authority: {
      title: 'Road Authority & Municipal Triage',
      desc: 'Review, verify, and prioritize citizen hazard observations and automated YOLO damage detections.',
      phase: 'Phase 2, 3 & 7'
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 antialiased">
      <DisclaimerBanner />
      <Navbar
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
        loadingHealth={loadingHealth}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Top Overview Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Persona Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-xs uppercase font-mono tracking-wider text-sky-700 font-semibold">
                  Active Persona Scope
                </span>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 font-mono font-medium">
                  {roleDescriptions[currentRole].phase}
                </span>
              </div>
              <h2 className="text-base font-bold text-slate-900 mt-3.5 flex items-center gap-2">
                {roleDescriptions[currentRole].title}
              </h2>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                {roleDescriptions[currentRole].desc}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-sky-600 shrink-0" />
              <span>Use the header demo role switcher to preview other persona views.</span>
            </div>
          </div>

          {/* Database Connectivity Diagnostics */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between lg:col-span-2">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-sky-600" />
                  <h3 className="text-xs uppercase font-mono tracking-wider text-slate-700 font-semibold">
                    Backend & PostGIS Status Probe
                  </h3>
                </div>
                <button
                  onClick={checkHealth}
                  disabled={loadingHealth}
                  className="text-xs text-slate-500 hover:text-sky-600 flex items-center gap-1.5 transition-colors font-medium cursor-pointer disabled:opacity-50"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80">
                  <div className="text-[11px] font-medium text-slate-500">PostgreSQL Connection</div>
                  <div className="text-sm font-semibold mt-1.5 flex items-center gap-1.5">
                    {loadingHealth && !health ? (
                      <span className="text-slate-500 text-xs">Checking connection...</span>
                    ) : health?.database.connected ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        <span className="text-emerald-700">Connected</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                        <span className="text-rose-700">Offline / Awaiting Setup</span>
                      </>
                    )}
                  </div>
                  {health?.database.server_version && (
                    <div className="text-[10px] text-slate-400 font-mono mt-1 truncate">
                      {health.database.server_version.split(' on ')[0]}
                    </div>
                  )}
                  {health?.database.error && (
                    <div className="text-[10px] text-rose-600 font-mono mt-1.5 line-clamp-2">
                      {health.database.error}
                    </div>
                  )}
                </div>

                <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80">
                  <div className="text-[11px] font-medium text-slate-500">PostGIS Spatial Extension</div>
                  <div className="text-sm font-semibold mt-1.5 flex items-center gap-1.5">
                    {loadingHealth && !health ? (
                      <span className="text-slate-500 text-xs">Checking PostGIS...</span>
                    ) : health?.database.postgis_enabled ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        <span className="text-emerald-700">Enabled</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                        <span className="text-amber-800">Extension Pending</span>
                      </>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    {health?.database.postgis_version
                      ? `Version: ${health.database.postgis_version.split(' ')[0]}`
                      : 'Required for spatial indexing and corridor queries.'}
                  </div>
                </div>
              </div>
            </div>

            {health?.database.setup_guidance && (
              <div className="mt-4 p-3 rounded-xl bg-sky-50 border border-sky-200 text-[11px] text-sky-950 flex items-start gap-2">
                <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                <span>{health.database.setup_guidance}</span>
              </div>
            )}
          </div>
        </div>

        {/* Tab Content: Phase 3 AI Road Damage View vs. Map & Citizen Hazard View */}
        {activeTab === 'damage' ? (
          <DamageDetectionView onPrefillHazard={handlePrefillHazard} />
        ) : (
          <>
            {/* Map & Hazard Reporting Section */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-sky-600" />
                    Hazard Reporting & Map View
                  </h2>
                  <p className="text-xs text-slate-500">
                    Click anywhere on the map to set report coordinates, or switch to the AI Road Damage tab to inspect photos first.
                  </p>
                </div>
                <div className="text-xs text-slate-700 bg-white border border-slate-200 px-3.5 py-1.5 rounded-xl shadow-xs flex items-center gap-2 self-start sm:self-auto">
                  <span className="text-slate-500">Selected Pin:</span>
                  <span className="font-mono text-sky-700 font-semibold">
                    {selectedCoord.lat.toFixed(4)}, {selectedCoord.lon.toFixed(4)}
                  </span>
                </div>
              </div>

              <MapContainer
                initialLat={12.9716}
                initialLon={77.5946}
                onLocationSelect={(lat, lon) => setSelectedCoord({ lat, lon })}
                hazards={hazards}
                focusHazard={focusHazard}
              />
            </div>

            {/* Hazard Form + Report List Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <HazardReportForm
                selectedLat={selectedCoord.lat}
                selectedLon={selectedCoord.lon}
                onReportCreated={loadHazards}
                onRequestLocation={() => {
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                prefill={hazardPrefill}
              />

              <HazardReportList
                hazards={hazards}
                loading={loadingHazards}
                onSelectHazard={handleSelectHazard}
              />
            </div>
          </>
        )}

        {/* Modular Architecture Roadmap Highlights */}
        <div className="space-y-3 pt-2">
          <h3 className="text-xs uppercase font-mono tracking-wider text-slate-500 font-semibold flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-sky-600" />
            Approved Development Modules & Status
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Phase 2</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                  Active
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-900">Road Hazard Reporting</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Citizen photo uploads, hazard persistence in PostgreSQL/PostGIS, and map visualization.
              </p>
            </div>

            <div className="bg-white border border-indigo-200 p-5 rounded-2xl shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Phase 3</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium">
                  Active
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-900">Road Damage YOLO</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Cracks (D00/D10/D20) & potholes (D40) detection with advisory bounding box visualizer.
              </p>
            </div>

            <div className="bg-white/80 border border-slate-200/80 p-5 rounded-2xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600">Phase 4</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-800">Vehicle Safety Index</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Deterministic tyre tread wear (CMVR Rule 95) & brake pad analysis with advisory disclaimers.
              </p>
            </div>

            <div className="bg-white/80 border border-slate-200/80 p-5 rounded-2xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600">Phase 5</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-800">Accident Risk & SHAP</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                XGBoost classifier with TreeSHAP waterfall charts explaining individual risk factor contributions.
              </p>
            </div>

            <div className="bg-white/80 border border-slate-200/80 p-5 rounded-2xl shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600">Phase 6</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-800">Emergency Support</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Verified trauma hospital locator and advisory hazard-bypassing corridor routing.
              </p>
            </div>
          </div>
        </div>
      </main>

      <Footer health={health} />
    </div>
  );
};

export default App;
