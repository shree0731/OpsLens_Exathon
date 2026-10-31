import React from 'react';
import { ArrowRight, ShieldAlert, AlertTriangle } from 'lucide-react';
import type { BannerBlast } from '../../types/api';

interface BlastRadiusBannerProps {
  banner: BannerBlast | null;
  banners?: BannerBlast[];
  onShowDetails?: (nodeId: string) => void;
}

export const BlastRadiusBanner: React.FC<BlastRadiusBannerProps> = ({
  banner,
  banners = [],
  onShowDetails,
}) => {
  if (!banner && (!banners || banners.length === 0)) return null;

  const activeBanner = banner || banners[0];
  const isMultiple = banners.length > 1;

  return (
    <div className="absolute top-4 left-6 right-6 z-20 flex flex-col md:flex-row md:items-center justify-between gap-2 px-4 py-2.5 bg-rose-50 border border-rose-200/90 rounded-xl shadow-card backdrop-blur-sm animate-in fade-in slide-in-from-top duration-300">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="p-1.5 rounded-lg bg-rose-100 text-rose-600 flex-shrink-0">
          <ShieldAlert className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-rose-900">
              {isMultiple ? `Multiple Blast Radii Active (${banners.length} Sources):` : 'Blast Radius Active:'}
            </span>
            <span className="text-xs font-medium text-rose-800 truncate">{activeBanner.summary}</span>
          </div>

          {/* If multiple sources, show pill chips for each */}
          {isMultiple && (
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              {banners.map((b) => (
                <button
                  key={b.node_id}
                  onClick={() => onShowDetails && onShowDetails(b.node_id)}
                  className="px-2 py-0.5 rounded-md bg-white border border-rose-200 text-[11px] font-semibold text-rose-800 hover:bg-rose-100 transition-colors flex items-center gap-1"
                >
                  <span>{b.label}</span>
                  <span className="text-[10px] text-rose-500 font-mono">({b.affected_node_ids.length} affected)</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {onShowDetails && activeBanner.node_id !== 'multiple' && (
        <button
          onClick={() => onShowDetails(activeBanner.node_id)}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:text-rose-900 hover:bg-rose-100 rounded-lg transition-colors flex-shrink-0 self-start md:self-auto"
        >
          <span>Show details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
