import React from 'react';
import { Shield, MapPin, Gauge, Ambulance, Layers, Server } from 'lucide-react';
import { UserRole, HealthResponse } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

interface NavbarProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  health: HealthResponse | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentRole,
  onRoleChange,
  activeTab,
  onTabChange,
  health
}) => {
  const roles: { id: UserRole; label: string; icon: React.ReactNode }[] = [
    { id: 'driver', label: 'Driver', icon: <MapPin className="w-3.5 h-3.5" /> },
    { id: 'buyer', label: 'Vehicle Buyer', icon: <Gauge className="w-3.5 h-3.5" /> },
    { id: 'ambulance', label: 'Ambulance Team', icon: <Ambulance className="w-3.5 h-3.5" /> },
    { id: 'authority', label: 'Road Authority', icon: <Shield className="w-3.5 h-3.5" /> },
  ];

  const tabs = [
    { id: 'map', label: 'Map & Live Overview', icon: <Layers className="w-4 h-4" /> },
    { id: 'hazards', label: 'Road Hazards', badge: 'Phase 2' },
    { id: 'vehicle', label: 'Vehicle Safety', badge: 'Phase 4' },
    { id: 'risk', label: 'Accident Risk & SHAP', badge: 'Phase 5' },
    { id: 'emergency', label: 'Emergency Support', badge: 'Phase 6' },
  ];

  const getHealthBadge = () => {
    if (!health) {
      return <StatusBadge status="Connecting..." variant="neutral" pulse />;
    }
    if (health.status === 'healthy') {
      return <StatusBadge status="API & PostGIS Healthy" variant="success" />;
    }
    if (health.database.connected) {
      return <StatusBadge status="DB Connected (PostGIS Missing)" variant="warning" />;
    }
    return <StatusBadge status="Backend Disconnected" variant="danger" />;
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-base tracking-tight">AI-Road-Safety</span>
                <span className="px-1.5 py-0.5 text-[10px] uppercase font-mono bg-sky-950 text-sky-400 border border-sky-800/50 rounded">
                  Phase 1 MVP
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">Road Hazard & Vehicle Risk Intelligence</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-slate-800 text-sky-400 border border-slate-700 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                  {tab.badge && (
                    <span className="text-[9px] px-1 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60 font-mono">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Persona Demo Switcher & Health Status */}
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center bg-slate-950/80 p-1 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 px-2 flex items-center gap-1">
                Demo Role:
              </span>
              {roles.map((r) => (
                <button
                  key={r.id}
                  onClick={() => onRoleChange(r.id)}
                  className={`px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1 transition-all ${
                    currentRole === r.id
                      ? 'bg-sky-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  title={`Switch view to ${r.label} perspective (UI Demo Tool)`}
                >
                  {r.icon}
                  <span className="hidden xl:inline">{r.label}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-400 hidden sm:block" />
              {getHealthBadge()}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
