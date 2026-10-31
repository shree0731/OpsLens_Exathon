import React, { useState, useEffect } from 'react';
import { 
  useInjectFaultMutation, 
  useResetFaultsMutation, 
  useFaultStatus,
  QUERY_KEYS 
} from '../../api/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { Zap, RotateCcw, ChevronDown, Loader2 } from 'lucide-react';

const FAULTS_OPTIONS = [
  { id: 'stale_feed', name: 'Stale Feed (Energy/Weather)' },
  { id: 'row_drop', name: 'Row Drop (-40% Orders)' },
  { id: 'schema_change', name: 'Schema Drift (Extra Col)' },
  { id: 'duplicates', name: 'Duplicate Keys (Lineitem)' },
  { id: 'revenue_mismatch', name: 'Revenue Mismatch ($ Gap)' },
  { id: 'job_failure', name: 'Job Failure (OOM Crash)' },
  { id: 'late_load', name: 'Late Load (SLA Delay)' },
];

export const MiniFaultToolbar: React.FC = () => {
  const [selectedFault, setSelectedFault] = useState<string>('stale_feed');
  const [resetStep, setResetStep] = useState<number>(0);

  const queryClient = useQueryClient();
  const { data: faultStatus } = useFaultStatus();
  const injectMutation = useInjectFaultMutation();
  const resetMutation = useResetFaultsMutation();

  const isResetting = resetMutation.isPending;
  const isInjecting = injectMutation.isPending;
  const isBusy = isResetting || isInjecting;

  const activeFaultNames = (faultStatus?.active_faults || []).map((f) => f.fault_name);

  // Progressive reset message over the ~7s duration
  useEffect(() => {
    let timer: any;
    if (isResetting) {
      setResetStep(1);
      timer = setInterval(() => {
        setResetStep((prev) => (prev < 4 ? prev + 1 : prev));
      }, 1600);
    } else {
      setResetStep(0);
    }
    return () => clearInterval(timer);
  }, [isResetting]);

  const getResetMessage = () => {
    switch (resetStep) {
      case 1:
        return 'Reloading tables 1/4...';
      case 2:
        return 'Reloading tables 2/4...';
      case 3:
        return 'Reloading tables 3/4...';
      case 4:
        return 'Restoring 100% trust...';
      default:
        return 'Reset';
    }
  };

  const handleInject = async () => {
    try {
      await injectMutation.mutateAsync(selectedFault);
      queryClient.invalidateQueries();
    } catch (err) {
      console.error('Failed to inject fault:', err);
    }
  };

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync();
      queryClient.invalidateQueries();
    } catch (err) {
      console.error('Failed to reset:', err);
    }
  };

  return (
    <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200/90 rounded-xl px-2 py-1 shadow-soft">
      {/* Compact Fault Dropdown */}
      <div className="relative">
        <select
          value={selectedFault}
          onChange={(e) => setSelectedFault(e.target.value)}
          disabled={isBusy}
          className="appearance-none bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-[11px] font-medium rounded-lg pl-2 pr-6 py-1 outline-none focus:ring-1 focus:ring-brand-500 transition-colors disabled:opacity-50 cursor-pointer max-w-[170px] truncate"
        >
          {FAULTS_OPTIONS.map((f) => {
            const isActive = activeFaultNames.includes(f.id);
            return (
              <option key={f.id} value={f.id}>
                {isActive ? '● ' : ''}{f.name}
              </option>
            );
          })}
        </select>
        <ChevronDown className="w-3 h-3 text-slate-400 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>

      {/* Inject Button */}
      <button
        onClick={handleInject}
        disabled={isBusy}
        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-navy-900 hover:bg-navy-800 active:bg-navy-700 text-white shadow-soft transition-colors disabled:opacity-50"
      >
        {isInjecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3 text-amber-300" />}
        <span>Inject</span>
      </button>

      {/* Reset Button with Progress Indicator */}
      <button
        onClick={handleReset}
        disabled={isBusy}
        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-200 shadow-soft transition-colors disabled:opacity-50 min-w-[70px] justify-center"
      >
        {isResetting ? (
          <>
            <Loader2 className="w-3 h-3 animate-spin text-brand-600" />
            <span className="text-[10px] text-brand-700 font-mono">{getResetMessage()}</span>
          </>
        ) : (
          <>
            <RotateCcw className="w-3 h-3 text-slate-400" />
            <span>Reset</span>
          </>
        )}
      </button>
    </div>
  );
};
