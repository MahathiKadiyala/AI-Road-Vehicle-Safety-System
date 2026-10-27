import React, { useState } from 'react';
import { Shield, MapPin, Gauge, Ambulance, Layers, Server, Menu, X, Sparkles } from 'lucide-react';
import { UserRole, HealthResponse } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { computeHealthState } from '../../services/api';

interface NavbarProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  health: HealthResponse | null;
  loadingHealth?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentRole,
  onRoleChange,
  activeTab,
  onTabChange,
  health,
  loadingHealth = false,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const roles: { id: UserRole; label: string; icon: React.ReactNode }[] = [
    { id: 'driver', label: 'Driver', icon: <MapPin className="w-3.5 h-3.5" /> },
    { id: 'buyer', label: 'Vehicle Buyer', icon: <Gauge className="w-3.5 h-3.5" /> },
    { id: 'ambulance', label: 'Ambulance Team', icon: <Ambulance className="w-3.5 h-3.5" /> },
    { id: 'authority', label: 'Road Authority', icon: <Shield className="w-3.5 h-3.5" /> },
  ];

  const tabs = [
    { id: 'map', label: 'Map & Live Overview', icon: <Layers className="w-4 h-4" /> },
    { id: 'hazards', label: 'Road Hazards', badge: 'Phase 2' },
    { id: 'damage', label: 'AI Road Damage', badge: 'Phase 3', icon: <Sparkles className="w-3.5 h-3.5 text-indigo-500" /> },
    { id: 'vehicle', label: 'Vehicle Safety', badge: 'Phase 4' },
    { id: 'risk', label: 'Accident Risk & SHAP', badge: 'Phase 5' },
    { id: 'emergency', label: 'Emergency Support', badge: 'Phase 6' },
  ];

  const healthState = computeHealthState(health, loadingHealth);

  const getHealthBadge = () => {
    switch (healthState) {
      case 'connecting':
        return <StatusBadge status="Connecting..." variant="neutral" pulse />;
      case 'healthy':
        return <StatusBadge status="System Healthy" variant="success" />;
      case 'degraded_postgis':
        return <StatusBadge status="DB Connected (PostGIS Missing)" variant="warning" />;
      case 'degraded_db':
        return <StatusBadge status="Backend Online · DB Offline" variant="warning" />;
      case 'offline':
      default:
        return <StatusBadge status="Backend Offline" variant="danger" />;
    }
  };

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-base tracking-tight">AI-Road-Safety</span>
                <span className="px-1.5 py-0.5 text-[10px] uppercase font-mono bg-indigo-50 text-indigo-700 border border-indigo-200 rounded font-semibold">
                  Phase 3 Active
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">Road Hazard & Vehicle Risk Intelligence</p>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav aria-label="Main Navigation" className="hidden lg:flex items-center gap-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-slate-100 text-sky-700 border border-slate-200/90 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                  {tab.badge && (
                    <span className="text-[9px] px-1 rounded bg-slate-100 text-slate-500 border border-slate-200 font-mono">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Desktop Persona Switcher & Health Status */}
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200">
              <span className="text-[10px] font-mono text-slate-500 px-2 flex items-center gap-1">
                Demo Role:
              </span>
              {roles.map((r) => (
                <button
                  key={r.id}
                  onClick={() => onRoleChange(r.id)}
                  className={`px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1 transition-all ${
                    currentRole === r.id
                      ? 'bg-white text-sky-700 shadow-sm border border-slate-200/80 font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
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

            {/* Mobile / Tablet Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile & Tablet Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-slate-200 space-y-4 animate-in fade-in duration-200">
            {/* Mobile Navigation Tabs */}
            <div className="space-y-1">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 pb-1 font-semibold">
                Navigation
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {tabs.map((tab) => {
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => {
                        onTabChange(tab.id);
                        setMobileMenuOpen(false);
                      }}
                      className={`w-full px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-between ${
                        isActive
                          ? 'bg-sky-50 text-sky-700 border border-sky-200/80 font-semibold'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {tab.icon}
                        {tab.label}
                      </span>
                      {tab.badge && (
                        <span className="text-[9px] px-1 rounded bg-slate-100 text-slate-500 border border-slate-200 font-mono">
                          {tab.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Mobile Persona Switcher */}
            <div className="space-y-1 pt-2 border-t border-slate-100">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 pb-1 font-semibold">
                Demo Role Perspective
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {roles.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => {
                      onRoleChange(r.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                      currentRole === r.id
                        ? 'bg-sky-600 text-white shadow-sm font-semibold'
                        : 'bg-slate-50 text-slate-700 border border-slate-200/60 hover:bg-slate-100'
                    }`}
                  >
                    {r.icon}
                    <span>{r.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
