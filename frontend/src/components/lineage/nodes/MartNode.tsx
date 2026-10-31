import React from 'react';
import { BaseLineageNode, BaseNodeData } from './BaseLineageNode';
import { Layers } from 'lucide-react';

export const MartNode: React.FC<{ data: BaseNodeData }> = ({ data }) => {
  return (
    <BaseLineageNode
      data={data}
      icon={<Layers className="w-3.5 h-3.5 text-amber-600" />}
      categoryLabel="Analytical Mart"
      hasTargetHandle={true}
      hasSourceHandle={true}
    />
  );
};
