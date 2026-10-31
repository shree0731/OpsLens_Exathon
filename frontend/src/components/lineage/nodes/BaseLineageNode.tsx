import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { TrustRing } from '../../common/TrustRing';
import { getStatusColor, StatusLevel } from '../../../styles/tokens';
import { AlertCircle } from 'lucide-react';
import type { LineageNode } from '../../../types/api';

export interface BaseNodeData extends LineageNode {
  isDimmed?: boolean;
  isBlastAffected?: boolean;
  isSelected?: boolean;
}

interface BaseLineageNodeProps {
  data: BaseNodeData;
  icon: React.ReactNode;
  categoryLabel: string;
  hasTargetHandle?: boolean;
  hasSourceHandle?: boolean;
}

export const BaseLineageNode: React.FC<BaseLineageNodeProps> = ({
  data,
  icon,
  categoryLabel,
  hasTargetHandle = true,
  hasSourceHandle = true,
}) => {
  const normStatus = (data.status || 'GREEN').toUpperCase() as StatusLevel;
  const colors = getStatusColor(normStatus);

  const isDegraded = normStatus !== 'GREEN' || (data.active_alerts && data.active_alerts.length > 0);
  const isBlastAffected = data.isBlastAffected;
  const isDimmed = data.isDimmed;

  // Pulse animation class if degraded or affected
  const pulseClass = isDegraded
    ? normStatus === 'RED'
      ? 'animate-pulse-ring-red'
      : 'animate-pulse-ring-amber'
    : isBlastAffected
    ? 'animate-pulse-ring-red'
    : '';

  return (
    <div
      className={`relative w-[230px] rounded-xl bg-white border transition-all duration-200 cursor-pointer select-none ${
        data.isSelected
          ? 'border-brand-600 ring-2 ring-brand-200 shadow-elevated'
          : isDegraded || isBlastAffected
          ? 'border-rose-400 shadow-card'
          : 'border-slate-200 hover:border-slate-300 shadow-soft hover:shadow-card'
      } ${pulseClass} ${isDimmed ? 'opacity-35 grayscale-[20%]' : 'opacity-100'}`}
    >
      {/* Target Handle (Left) */}
      {hasTargetHandle && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-white hover:!bg-brand-500"
        />
      )}

      {/* Main Node Content */}
      <div className="p-3">
        {/* Category & Status Header */}
        <div className="flex items-center justify-between gap-1 mb-2">
          <div className="flex items-center gap-1.5 text-slate-500">
            <span className="p-1 rounded-md bg-slate-50 text-slate-600 border border-slate-100">
              {icon}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {categoryLabel}
            </span>
          </div>

          {/* Active Alert Icon Badge */}
          {((data.active_alerts && data.active_alerts.length > 0) || (data.inherited_from && data.inherited_from.length > 0)) && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold"
              style={{ backgroundColor: colors.bg, color: colors.text }}
            >
              <AlertCircle className="w-3 h-3" />
              <span>{(data.active_alerts?.length || 0) + (data.inherited_from?.length || 0)}</span>
            </span>
          )}
        </div>

        {/* Node Label & Trust Ring */}
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p
              className="text-xs font-semibold text-slate-900 truncate"
              title={data.label}
            >
              {data.label}
            </p>
            <p className="text-[10px] text-slate-400 truncate font-mono">
              {data.id}
            </p>
          </div>

          <TrustRing
            score={data.trust_score ?? 100}
            status={normStatus}
            size={34}
            strokeWidth={3}
          />
        </div>
      </div>

      {/* Source Handle (Right) */}
      {hasSourceHandle && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-white hover:!bg-brand-500"
        />
      )}
    </div>
  );
};
