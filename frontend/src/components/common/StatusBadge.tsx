import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant = 'neutral',
  pulse = false
}) => {
  const variantStyles = {
    success: 'bg-emerald-950/80 text-emerald-400 border-emerald-700/50',
    warning: 'bg-amber-950/80 text-amber-400 border-amber-700/50',
    danger: 'bg-rose-950/80 text-rose-400 border-rose-700/50',
    info: 'bg-sky-950/80 text-sky-400 border-sky-700/50',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700'
  };

  const dotColors = {
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    danger: 'bg-rose-400',
    info: 'bg-sky-400',
    neutral: 'bg-slate-400'
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotColors[variant]} ${pulse ? 'animate-pulse' : ''}`} />
      {status}
    </span>
  );
};
