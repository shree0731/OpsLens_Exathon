import React, { useState } from 'react';
import { LineageCanvas } from '../components/lineage/LineageCanvas';
import { LineageToolbar } from '../components/lineage/LineageToolbar';
import { ErrorToast } from '../components/common/ErrorToast';
import { useLineageGraph } from '../api/hooks';

export const LineagePage: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useLineageGraph(5000);

  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error' | 'info';
  } | null>(null);

  const handleFeedback = (message: string, type: 'success' | 'error' | 'info') => {
    setToast({ message, type });
    refetch();
  };

  return (
    <div className="relative h-full flex flex-col gap-4">
      {/* Floating Canvas Action Toolbar */}
      <LineageToolbar onActionFeedback={handleFeedback} />

      {/* Main Canvas Component */}
      <div className="flex-1 min-h-0">
        <LineageCanvas
          data={data}
          isLoading={isLoading}
          isError={isError}
          error={error}
          onRetry={() => refetch()}
        />
      </div>

      {/* Toast Notification */}
      {toast && (
        <ErrorToast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};
