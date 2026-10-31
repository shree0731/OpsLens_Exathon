import React, { useState } from 'react';
import { PrimaryButton } from '../common/PrimaryButton';
import { SecondaryButton } from '../common/SecondaryButton';
import { 
  useInjectFaultMutation, 
  useResetFaultsMutation, 
  useRunChecksMutation, 
  useFaultStatus 
} from '../../api/hooks';
import { Zap, RotateCcw, Play, CheckCircle2, ChevronDown } from 'lucide-react';

const FAULTS_OPTIONS = [
  { id: 'late_load', name: 'Late Load (SLA Delay)' },
  { id: 'row_drop', name: 'Row Drop (-40% Orders)' },
  { id: 'schema_change', name: 'Schema Drift (Extra Col)' },
  { id: 'duplicates', name: 'Duplicate Keys (Lineitem)' },
  { id: 'revenue_mismatch', name: 'Revenue Mismatch ($ Gap)' },
  { id: 'stale_feed', name: 'Stale Feed (Energy/Weather)' },
  { id: 'job_failure', name: 'Job Failure (OOM Crash)' },
];

interface LineageToolbarProps {
  onActionFeedback: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const LineageToolbar: React.FC<LineageToolbarProps> = ({ onActionFeedback }) => {
  const [selectedFault, setSelectedFault] = useState<string>('stale_feed');

  const { data: faultStatus } = useFaultStatus();
  const injectMutation = useInjectFaultMutation();
  const resetMutation = useResetFaultsMutation();
  const runChecksMutation = useRunChecksMutation();

  const isBusy = injectMutation.isPending || resetMutation.isPending || runChecksMutation.isPending;

  const activeFaultNames = (faultStatus?.active_faults || []).map((f) => f.fault_name);

  const handleInject = async () => {
    try {
      const res = await injectMutation.mutateAsync(selectedFault);
      const alertCount = res.new_alerts_count ?? 1;
      onActionFeedback(
        `Injected '${selectedFault}' — ${alertCount} new alert${alertCount === 1 ? '' : 's'} opened`,
        'error'
      );
    } catch (err: any) {
      onActionFeedback(err.message || 'Failed to inject fault', 'error');
    }
  };

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync();
      onActionFeedback('Reset completed: all tables reloaded and alerts auto-resolved', 'success');
    } catch (err: any) {
      onActionFeedback(err.message || 'Failed to reset tables', 'error');
    }
  };

  const handleRunChecks = async () => {
    try {
      const res = await runChecksMutation.mutateAsync();
      const openCount = res?.alerts_active ?? 0;
      onActionFeedback(`Sentinel executed: ${openCount} open alerts active across 21 checks`, 'info');
    } catch (err: any) {
      onActionFeedback(err.message || 'Sentinel checks failed', 'error');
    }
  };

  return (
    <div className="absolute top-4 right-6 z-20 flex items-center gap-2.5 bg-white/95 backdrop-blur-md p-1.5 rounded-xl border border-slate-200/90 shadow-card">
      {/* Fault Selector Dropdown */}
      <div className="relative">
        <select
          value={selectedFault}
          onChange={(e) => setSelectedFault(e.target.value)}
          disabled={isBusy}
          className="appearance-none bg-slate-50 hover:bg-slate-100/80 border border-slate-200 text-slate-800 text-xs font-medium rounded-lg pl-3 pr-8 py-2 outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-colors disabled:opacity-50 cursor-pointer"
        >
          {FAULTS_OPTIONS.map((f) => {
            const isActive = activeFaultNames.includes(f.id);
            return (
              <option key={f.id} value={f.id}>
                {f.name} {isActive ? '● (Active)' : ''}
              </option>
            );
          })}
        </select>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>

      {/* Inject Button */}
      <PrimaryButton
        onClick={handleInject}
        loading={injectMutation.isPending}
        disabled={isBusy}
        icon={<Zap className="w-3.5 h-3.5 text-amber-300" />}
        variant="primary"
        className="!text-xs !py-1.5 !px-3"
      >
        Inject Fault
      </PrimaryButton>

      {/* Reset Button */}
      <SecondaryButton
        onClick={handleReset}
        loading={resetMutation.isPending}
        disabled={isBusy}
        icon={<RotateCcw className="w-3.5 h-3.5 text-slate-500" />}
        className="!text-xs !py-1.5 !px-3"
      >
        Reset Clean
      </SecondaryButton>

      <div className="h-5 w-px bg-slate-200 mx-0.5" />

      {/* Run Checks Button */}
      <SecondaryButton
        onClick={handleRunChecks}
        loading={runChecksMutation.isPending}
        disabled={isBusy}
        icon={<Play className="w-3.5 h-3.5 text-brand-600" />}
        className="!text-xs !py-1.5 !px-3"
      >
        Run Checks
      </SecondaryButton>
    </div>
  );
};
