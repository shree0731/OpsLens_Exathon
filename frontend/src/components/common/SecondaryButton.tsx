import React from 'react';
import { Loader2 } from 'lucide-react';

interface SecondaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  icon?: React.ReactNode;
}

export const SecondaryButton: React.FC<SecondaryButtonProps> = ({
  children,
  loading = false,
  disabled,
  icon,
  className = '',
  ...props
}) => {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-3.5 py-2 text-sm font-medium bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg shadow-soft transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin text-slate-500" /> : icon}
      <span>{children}</span>
    </button>
  );
};
