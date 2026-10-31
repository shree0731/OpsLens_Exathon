import React from 'react';
import { BaseLineageNode, BaseNodeData } from './BaseLineageNode';
import { Table2 } from 'lucide-react';

export const TableNode: React.FC<{ data: BaseNodeData }> = ({ data }) => {
  return (
    <BaseLineageNode
      data={data}
      icon={<Table2 className="w-3.5 h-3.5 text-emerald-600" />}
      categoryLabel="Production Table"
      hasTargetHandle={true}
      hasSourceHandle={true}
    />
  );
};
