import React from 'react';
import { BaseLineageNode, BaseNodeData } from './BaseLineageNode';
import { Radio } from 'lucide-react';

export const SourceNode: React.FC<{ data: BaseNodeData }> = ({ data }) => {
  return (
    <BaseLineageNode
      data={data}
      icon={<Radio className="w-3.5 h-3.5 text-blue-600" />}
      categoryLabel="Source Feed"
      hasTargetHandle={false}
      hasSourceHandle={true}
    />
  );
};
