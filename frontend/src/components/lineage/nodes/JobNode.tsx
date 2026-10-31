import React from 'react';
import { BaseLineageNode, BaseNodeData } from './BaseLineageNode';
import { Cog } from 'lucide-react';

export const JobNode: React.FC<{ data: BaseNodeData }> = ({ data }) => {
  return (
    <BaseLineageNode
      data={data}
      icon={<Cog className="w-3.5 h-3.5 text-purple-600" />}
      categoryLabel="Pipeline Job"
      hasTargetHandle={true}
      hasSourceHandle={true}
    />
  );
};
