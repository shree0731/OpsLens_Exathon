import React from 'react';
import { getStatusColor, StatusLevel } from '../../styles/tokens';

interface TrustRingProps {
  score: number;
  status: StatusLevel | string;
  size?: number;
  strokeWidth?: number;
  showScore?: boolean;
}

export const TrustRing: React.FC<TrustRingProps> = ({
  score,
  status,
  size = 40,
  strokeWidth = 3.5,
  showScore = true,
}) => {
  const normStatus = (status || 'GREEN').toUpperCase() as StatusLevel;
  const colors = getStatusColor(normStatus);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke="#E2E8F0"
          strokeWidth={strokeWidth}
        />
        {/* Colored progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke={colors.base}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {showScore && (
        <span
          className="absolute text-[11px] font-semibold tracking-tight"
          style={{ color: colors.text }}
        >
          {Math.round(score)}
        </span>
      )}
    </div>
  );
};
