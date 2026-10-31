import React from 'react';
import { useHealth } from '../../api/hooks';
import { StatusBadge } from '../common/StatusBadge';
import { MiniFaultToolbar } from './MiniFaultToolbar';
import { Activity, Database, AlertCircle } from 'lucide-react';

interface TopBarProps {
  pageTitle?: string;
}

export const TopBar: React.FC<TopBarProps> = ({ pageTitle = 'Data Pipeline Lineage' }) => {
  const { data: health, isLoading } = useHealth(6000);

  const openAlerts = health?.open_alerts_count ?? 0;
  const avgTrust = health?.average_trust_score ?? 100.0;
  const overallStatus = openAlerts > 0 ? (openAlerts > 1 ? 'RED' : 'AMBER') : 'GREEN';

  return (
    <header className="h-16 px-6 bg-white/80 backdrop-blur-sm border-b border-slate-200/80 flex items-center justify-between sticky top-0 z-30">
      {/* Page Title & Breadcrumb */}
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold text-slate-900 tracking-tight">{pageTitle}</h2>
        <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
          <Database className="w-3 h-3 text-slate-500" />
          Exasol Personal Edition
        </span>
      </div>

      {/* Persistent Mini Fault Toolbar & Live Status Chip */}
      <div className="flex items-center gap-3">
        {/* Global Mini Fault Toolbar */}
        <MiniFaultToolbar />

        {/* Global Simulated Data Chip */}
        <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200/80">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          Simulated
        </span>

        {/* Live Cluster Health & Trust Chip */}
        <div className="flex items-center gap-3 bg-white px-3.5 py-1.5 rounded-xl border border-slate-200 shadow-soft">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-400" />
            <span className="text-xs text-slate-500 font-medium hidden sm:inline">Trust:</span>
            <span className="text-xs font-bold text-slate-900">
              {isLoading ? '...' : `${avgTrust.toFixed(1)}%`}
            </span>
          </div>

          <div className="h-4 w-px bg-slate-200" />

          <div className="flex items-center gap-1.5">
            {openAlerts > 0 ? (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600">
                <AlertCircle className="w-3.5 h-3.5" />
                {openAlerts} {openAlerts === 1 ? 'alert' : 'alerts'}
              </span>
            ) : (
              <span className="text-xs font-medium text-emerald-600">0 alerts</span>
            )}
          </div>

          <StatusBadge status={overallStatus} size="sm" showIcon={false} />
        </div>
      </div>
    </header>
  );
};
