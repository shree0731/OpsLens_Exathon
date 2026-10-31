import React from 'react';
import { BaseLineageNode, BaseNodeData } from './BaseLineageNode';
import { LayoutDashboard } from 'lucide-react';

export const DashboardNode: React.FC<{ data: BaseNodeData }> = ({ data }) => {
  return (
    <BaseLineageNode
      data={data}
      icon={<LayoutDashboard className="w-3.5 h-3.5 text-indigo-600" />}
      categoryLabel="BI Dashboard"
      hasTargetHandle={true}
      hasSourceHandle={false}
    />
  );
};
