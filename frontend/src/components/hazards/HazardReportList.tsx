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

const severityStyles: Record<string, { bg: string; text: string; dot: string }> = {
  low: { bg: 'bg-emerald-950/50', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  medium: { bg: 'bg-amber-950/50', text: 'text-amber-400', dot: 'bg-amber-400' },
  high: { bg: 'bg-orange-950/50', text: 'text-orange-400', dot: 'bg-orange-400' },
  critical: { bg: 'bg-rose-950/50', text: 'text-rose-400', dot: 'bg-rose-400' },
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
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg">
        <div className="flex items-center justify-center gap-2 text-slate-400 text-sm">
          <div className="w-4 h-4 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
          Loading hazard reports...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-lg overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <FileWarning className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold text-white">Saved Hazard Reports</h3>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono">
          {hazards.length} report{hazards.length !== 1 ? 's' : ''}
        </span>
      </div>

      {hazards.length === 0 ? (
        <div className="px-5 py-8 text-center">
          <AlertTriangle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-400">No hazard reports yet.</p>
          <p className="text-[11px] text-slate-500 mt-1">
            Use the form above to submit your first citizen report.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-slate-800/60 max-h-[400px] overflow-y-auto">
          {hazards.map((hazard) => {
            const sv = severityStyles[hazard.severity] || severityStyles.medium;
            const imageUrl = getHazardImageUrl(hazard.image_url);

            return (
              <button
                key={hazard.id}
                onClick={() => onSelectHazard?.(hazard)}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-800/40 transition-colors text-left group"
              >
                {/* Thumbnail or type icon */}
                <div className="shrink-0 w-12 h-12 rounded-xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center">
                  {imageUrl ? (
                    <img src={imageUrl} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-lg">{hazardTypeEmoji[hazard.hazard_type] || '⚠️'}</span>
                  )}
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white truncate">
                      {hazard.title}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${sv.bg} ${sv.text} border-current/20`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${sv.dot}`} />
                      {hazard.severity}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {hazard.latitude.toFixed(4)}, {hazard.longitude.toFixed(4)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatRelativeTime(hazard.created_at)}
                    </span>
                    {hazard.image_url && (
                      <span className="flex items-center gap-0.5 text-sky-400">
                        <ImageIcon className="w-3 h-3" />
                        photo
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {hazardTypeEmoji[hazard.hazard_type]} {hazard.hazard_type} · {hazard.source.replace('_', ' ')} · {hazard.status}
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-sky-400 transition-colors shrink-0" />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
