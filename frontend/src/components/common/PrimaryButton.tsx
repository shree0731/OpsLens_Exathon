import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  icon?: React.ReactNode;
  variant?: 'primary' | 'danger';
}

export const PrimaryButton: React.FC<ButtonProps> = ({
  children,
  loading = false,
  disabled,
  icon,
  variant = 'primary',
  className = '',
  ...props
}) => {
  const baseColors =
    variant === 'danger'
      ? 'bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-rose-200'
      : 'bg-navy-900 hover:bg-navy-800 active:bg-navy-700 text-white shadow-slate-200';

  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg shadow-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${baseColors} ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      <span>{children}</span>
    </button>
  );
};
