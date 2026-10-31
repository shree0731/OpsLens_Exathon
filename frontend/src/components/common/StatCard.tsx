import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    positive?: boolean;
  };
  statusColor?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  statusColor,
}) => {
  return (
    <div className="bg-white rounded-xl p-4 border border-slate-100 shadow-card flex items-start justify-between">
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 tracking-tight" style={statusColor ? { color: statusColor } : undefined}>
            {value}
          </span>
          {trend && (
            <span
              className={`text-xs font-semibold ${
                trend.positive ? 'text-emerald-600' : 'text-rose-600'
              }`}
            >
              {trend.value}
            </span>
          )}
        </div>
        {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
      </div>
      {icon && (
        <div className="p-2.5 rounded-lg bg-slate-50 text-slate-600 border border-slate-100">
          {icon}
        </div>
      )}
    </div>
  );
};
