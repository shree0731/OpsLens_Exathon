import React from 'react';
import { AlertTriangle, ArrowRight, ShieldAlert } from 'lucide-react';
import type { BannerBlast } from '../../types/api';

interface BlastRadiusBannerProps {
  banner: BannerBlast | null;
  onShowDetails?: (nodeId: string) => void;
}

export const BlastRadiusBanner: React.FC<BlastRadiusBannerProps> = ({
  banner,
  onShowDetails,
}) => {
  if (!banner) return null;

  return (
    <div className="absolute top-4 left-6 right-6 z-20 flex items-center justify-between px-4 py-2.5 bg-rose-50 border border-rose-200/90 rounded-xl shadow-card backdrop-blur-sm animate-in fade-in slide-in-from-top duration-300">
      <div className="flex items-center gap-2.5">
        <div className="p-1.5 rounded-lg bg-rose-100 text-rose-600 flex-shrink-0">
          <ShieldAlert className="w-4 h-4" />
        </div>
        <div>
          <span className="text-xs font-bold text-rose-900 mr-2">Blast Radius Active:</span>
          <span className="text-xs font-medium text-rose-800">{banner.summary}</span>
        </div>
      </div>

      {onShowDetails && (
        <button
          onClick={() => onShowDetails(banner.node_id)}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:text-rose-900 hover:bg-rose-100 rounded-lg transition-colors flex-shrink-0"
        >
          <span>Show details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
