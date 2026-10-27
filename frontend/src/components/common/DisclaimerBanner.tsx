import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <aside aria-label="Regulatory Disclaimers" className="bg-amber-50 border-b border-amber-200/80 px-4 py-2 text-xs text-amber-900">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong className="font-semibold text-amber-950">Phase 2 Active — Hazard Reporting:</strong> Citizen-submitted hazard reports are user observations, not AI-verified detections. Vehicle assessments are preliminary evaluations and do not replace certified physical inspections. Emergency routing is advisory only.
          </span>
        </div>
        <span className="hidden md:inline-block px-2.5 py-0.5 rounded-full bg-amber-100/80 text-amber-800 font-mono text-[10px] border border-amber-200 font-medium">
          CMVR & AIS Compliant Architecture
        </span>
      </div>
    </aside>
  );
};
