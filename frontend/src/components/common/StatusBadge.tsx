import React from 'react';
import { StatusLevel, getStatusColor } from '../../styles/tokens';
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';

interface StatusBadgeProps {
  status: StatusLevel | string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
}) => {
  const norm = (status || 'GREEN').toUpperCase() as StatusLevel;
  const colors = getStatusColor(norm);

  const getIcon = () => {
    if (norm === 'RED') return <AlertOctagon className="w-3.5 h-3.5" />;
    if (norm === 'AMBER') return <AlertTriangle className="w-3.5 h-3.5" />;
    return <CheckCircle2 className="w-3.5 h-3.5" />;
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${sizeClasses}`}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      }}
    >
      {showIcon && getIcon()}
      <span>{norm}</span>
    </span>
  );
};
