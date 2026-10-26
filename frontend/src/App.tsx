import React, { useState, useEffect, useCallback } from 'react';
import { UserRole, HealthResponse, Hazard } from './types';
import { fetchHealthStatus, fetchHazardReports } from './services/api';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { DisclaimerBanner } from './components/common/DisclaimerBanner';
import { MapContainer } from './components/map/MapContainer';
import { HazardReportForm } from './components/hazards/HazardReportForm';
import { HazardReportList } from './components/hazards/HazardReportList';
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

  const checkHealth = async () => {
    setLoadingHealth(true);
    const data = await fetchHealthStatus();
    setHealth(data);
    setLoadingHealth(false);
  };

  const loadHazards = useCallback(async () => {
    setLoadingHazards(true);
    try {
      const data = await fetchHazardReports({ limit: 100 });
      setHazards(data);
    } catch (err) {
      console.warn('Could not fetch hazard reports:', err);
      // Don't clear existing hazards on transient error
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
    // Reset focus after animation completes
    setTimeout(() => setFocusHazard(null), 2000);
  }, []);

  const roleDescriptions: Record<UserRole, { title: string; desc: string; phase: string }> = {
    driver: {
      title: 'Citizen Driver Experience',
      desc: 'Report potholes and cracks with GPS and camera evidence, and view active route hazards on the map.',
      phase: 'Phase 2'
    },
    buyer: {
      title: 'Used-Vehicle Buyer Experience',
      desc: 'Transparent condition analysis for brake pad wear and tyre tread against CMVR Rule 95 legal standards.',
      phase: 'Phase 4'
    },
    ambulance: {
      title: 'Ambulance Emergency Support',
      desc: 'Advisory hazard-penalized routing and verified trauma hospital proximity analysis.',
      phase: 'Phase 6'
    },
    authority: {
      title: 'Road Authority & Municipal Triage',
      desc: 'Review, verify, and track citizen hazard reports through verification and repair workflows.',
      phase: 'Phase 2 & 7'
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <DisclaimerBanner />
      <Navbar
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Top Overview Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Persona Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-xs uppercase font-mono tracking-wider text-sky-400 font-semibold">
                  Active Persona Scope
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-sky-950 text-sky-300 border border-sky-800 font-mono">
                  {roleDescriptions[currentRole].phase}
                </span>
              </div>
              <h2 className="text-base font-bold text-white mt-3 flex items-center gap-2">
                {roleDescriptions[currentRole].title}
              </h2>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                {roleDescriptions[currentRole].desc}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>Use header switcher to preview other user workflows.</span>
            </div>
          </div>

          {/* Database Connectivity Diagnostics */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between lg:col-span-2">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-sky-400" />
                  <h3 className="text-xs uppercase font-mono tracking-wider text-slate-300 font-semibold">
                    Backend & PostGIS Status Probe
                  </h3>
                </div>
                <button
                  onClick={checkHealth}
                  disabled={loadingHealth}
                  className="text-xs text-slate-400 hover:text-sky-400 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
                <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">PostgreSQL Connection</div>
                  <div className="text-sm font-semibold mt-1 flex items-center gap-1.5">
                    {health?.database.connected ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-emerald-300">Connected</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        <span className="text-amber-300">Disconnected (Awaiting Setup)</span>
                      </>
                    )}
                  </div>
                  {health?.database.error && (
                    <div className="text-[10px] text-slate-400 font-mono mt-1.5 line-clamp-2">
                      {health.database.error}
                    </div>
                  )}
                </div>

                <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">PostGIS Spatial Extension</div>
                  <div className="text-sm font-semibold mt-1 flex items-center gap-1.5">
                    {health?.database.postgis_enabled ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-emerald-300">Enabled ({health.database.postgis_version})</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        <span className="text-amber-300">Pending Extension</span>
                      </>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1.5">
                    Required for spatial indexing in advanced queries.
                  </div>
                </div>
              </div>
            </div>

            {health?.database.setup_guidance && (
              <div className="mt-3 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 flex items-start gap-2">
                <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <span>{health.database.setup_guidance}</span>
              </div>
            )}
          </div>
        </div>

        {/* Map & Hazard Reporting Section */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <MapPin className="w-5 h-5 text-sky-400" />
                Hazard Reporting & Map View
              </h2>
              <p className="text-xs text-slate-400">
                Click the map to select a location, then use the form to submit a citizen hazard report.
              </p>
            </div>
            <div className="text-xs text-slate-300 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl flex items-center gap-2">
              <span className="text-slate-400">Selected:</span>
              <span className="font-mono text-sky-400 font-semibold">
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
              // Scroll to map section
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          />

          <HazardReportList
            hazards={hazards}
            loading={loadingHazards}
            onSelectHazard={handleSelectHazard}
          />
        </div>

        {/* Modular Architecture Roadmap Highlights */}
        <div className="space-y-3 pt-2">
          <h3 className="text-xs uppercase font-mono tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-sky-400" />
            Approved Development Modules & Status
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Phase 2</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                  Active
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">Road Hazard Reporting</h4>
              <p className="text-[11px] text-slate-400">
                Citizen photo uploads, hazard persistence, and interactive map visualization.
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Phase 4</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">Vehicle Safety Index</h4>
              <p className="text-[11px] text-slate-400">
                Deterministic tyre wear (CMVR Rule 95) & brake pad analysis with legal disclaimers.
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Phase 5</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">Accident Risk & SHAP</h4>
              <p className="text-[11px] text-slate-400">
                XGBoost classifier with TreeSHAP waterfall charts explaining risk contributions.
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Phase 6</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">Emergency Support</h4>
              <p className="text-[11px] text-slate-400">
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
