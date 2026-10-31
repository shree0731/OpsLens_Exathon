import React from 'react';
import { EmptyState } from '../components/common/EmptyState';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => {
  return (
    <div className="h-full flex items-center justify-center">
      <EmptyState
        title={title}
        description={description}
        icon={<Construction className="w-12 h-12 text-slate-300" />}
      />
    </div>
  );
};
