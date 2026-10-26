import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <div className="bg-amber-950/40 border-b border-amber-800/40 px-4 py-2 text-xs text-amber-200/90">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            <strong>Phase 2 Active — Hazard Reporting:</strong> Citizen-submitted hazard reports are user observations, not AI-verified detections. Vehicle assessments are preliminary evaluations and do not replace certified physical inspections. Emergency routing is advisory only.
          </span>
        </div>
        <span className="hidden md:inline-block px-2 py-0.5 rounded bg-amber-900/50 text-amber-300 font-mono text-[10px] border border-amber-700/40">
          CMVR & AIS Compliant Architecture
        </span>
      </div>
    </div>
  );
};
