import React from 'react';
import { Database, ShieldCheck, ExternalLink } from 'lucide-react';
import { HealthResponse } from '../../types';

interface FooterProps {
  health: HealthResponse | null;
}

export const Footer: React.FC<FooterProps> = ({ health }) => {
  return (
    <footer className="border-t border-slate-200 bg-white mt-auto py-6 px-4 text-xs text-slate-500 shadow-inner">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 text-center md:text-left justify-center md:justify-start">
          <div className="flex items-center gap-1.5 font-semibold text-slate-800">
            <ShieldCheck className="w-4 h-4 text-sky-600" />
            <span>AI-Road-Vehicle-Safety-System</span>
          </div>
          <span className="text-slate-300 hidden md:inline">|</span>
          <span className="text-slate-500">
            End-to-End Modular Architecture
          </span>
          <span className="text-slate-300 hidden md:inline">|</span>
          <span className="font-mono text-slate-500 text-[11px]">
            CMVR Rule 95 & AIS Benchmark Standard
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-600">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span>
              DB: {health?.database.connected ? 'PostgreSQL Active' : 'Offline / Awaiting Config'}
            </span>
            {health?.database.postgis_enabled && (
              <span className="text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded font-mono text-[10px]">
                PostGIS {health.database.postgis_version}
              </span>
            )}
          </div>

          <a
            href="http://127.0.0.1:8000/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1 transition-colors"
          >
            <span>FastAPI Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </footer>
  );
};
