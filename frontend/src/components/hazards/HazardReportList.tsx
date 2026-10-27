import React from 'react';
import { Hazard } from '../../types';
import { getHazardImageUrl } from '../../services/api';
import {
  AlertTriangle,
  MapPin,
  Clock,
  ImageIcon,
  ChevronRight,
  FileWarning,
} from 'lucide-react';

interface HazardReportListProps {
  hazards: Hazard[];
  loading: boolean;
  onSelectHazard?: (hazard: Hazard) => void;
}

const severityStyles: Record<string, { bg: string; text: string; dot: string; border: string }> = {
  low: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200' },
  medium: { bg: 'bg-amber-50', text: 'text-amber-800', dot: 'bg-amber-500', border: 'border-amber-200' },
  high: { bg: 'bg-orange-50', text: 'text-orange-800', dot: 'bg-orange-500', border: 'border-orange-200' },
  critical: { bg: 'bg-rose-50', text: 'text-rose-700', dot: 'bg-rose-500', border: 'border-rose-200' },
};

const hazardTypeEmoji: Record<string, string> = {
  pothole: '🕳️',
  crack: '⚡',
  debris: '🪨',
  waterlogging: '🌊',
  obstacle: '🚧',
  other: '⚠️',
};

function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export const HazardReportList: React.FC<HazardReportListProps> = ({
  hazards,
  loading,
  onSelectHazard,
}) => {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
        <div className="flex items-center justify-center gap-2.5 text-slate-600 text-sm">
          <div className="w-4 h-4 border-2 border-sky-600 border-t-transparent rounded-full animate-spin" />
          <span>Loading hazard reports...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <FileWarning className="w-4 h-4 text-amber-600" />
          <h3 className="text-base font-bold text-slate-900">Saved Hazard Reports</h3>
        </div>
        <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono font-medium">
          {hazards.length} report{hazards.length !== 1 ? 's' : ''}
        </span>
      </div>

      {hazards.length === 0 ? (
        <div className="px-5 py-12 text-center">
          <AlertTriangle className="w-9 h-9 text-slate-300 mx-auto mb-2.5" />
          <p className="text-sm font-semibold text-slate-700">No hazard reports recorded yet.</p>
          <p className="text-xs text-slate-500 mt-1">
            Click on the map and submit the form to record the first road hazard.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100 max-h-[430px] overflow-y-auto">
          {hazards.map((hazard) => {
            const sv = severityStyles[hazard.severity] || severityStyles.medium;
            const imageUrl = getHazardImageUrl(hazard.image_url);

            return (
              <button
                key={hazard.id}
                onClick={() => onSelectHazard?.(hazard)}
                className="w-full px-5 py-3.5 flex items-center gap-3.5 hover:bg-slate-50/80 transition-colors text-left group"
              >
                {/* Thumbnail or type icon */}
                <div className="shrink-0 w-12 h-12 rounded-xl overflow-hidden border border-slate-200 bg-slate-50 flex items-center justify-center shadow-xs">
                  {imageUrl ? (
                    <img src={imageUrl} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-lg">{hazardTypeEmoji[hazard.hazard_type] || '⚠️'}</span>
                  )}
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900 truncate">
                      {hazard.title}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${sv.bg} ${sv.text} ${sv.border}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${sv.dot}`} />
                      <span className="capitalize">{hazard.severity}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      {hazard.latitude.toFixed(4)}, {hazard.longitude.toFixed(4)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {formatRelativeTime(hazard.created_at)}
                    </span>
                    {hazard.image_url && (
                      <span className="flex items-center gap-0.5 text-sky-600 font-medium">
                        <ImageIcon className="w-3 h-3" />
                        photo
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5 capitalize">
                    {hazardTypeEmoji[hazard.hazard_type]} {hazard.hazard_type} · {hazard.source.replace('_', ' ')} · status: {hazard.status}
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-sky-600 group-hover:translate-x-0.5 transition-all shrink-0" />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
