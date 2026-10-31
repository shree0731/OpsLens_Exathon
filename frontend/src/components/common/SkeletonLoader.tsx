import React from 'react';

interface SkeletonLoaderProps {
  height?: string;
  className?: string;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  height = 'h-24',
  className = '',
}) => {
  return (
    <div
      className={`w-full bg-slate-200/80 rounded-2xl animate-pulse ${height} ${className}`}
    />
  );
};