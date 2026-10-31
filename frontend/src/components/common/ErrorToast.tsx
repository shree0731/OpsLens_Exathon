import React from 'react';
import { AlertCircle, X } from 'lucide-react';

interface ErrorToastProps {
  message: string;
  onClose?: () => void;
  type?: 'error' | 'success' | 'info';
}

export const ErrorToast: React.FC<ErrorToastProps> = ({
  message,
  onClose,
  type = 'error',
}) => {
  const styles =
    type === 'success'
      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
      : type === 'info'
      ? 'bg-blue-50 text-blue-800 border-blue-200'
      : 'bg-rose-50 text-rose-800 border-rose-200';

  return (
    <div
      className={`fixed bottom-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-elevated transition-all duration-200 ${styles}`}
    >
      <AlertCircle className="w-5 h-5 flex-shrink-0" />
      <span className="text-sm font-medium">{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1 hover:bg-black/5 rounded-lg transition-colors ml-2"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
