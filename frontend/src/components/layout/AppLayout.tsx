import React from 'react';
import { LeftRail } from './LeftRail';
import { TopBar } from './TopBar';

interface AppLayoutProps {
  children: React.ReactNode;
  pageTitle?: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, pageTitle }) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Left Navigation Rail */}
      <LeftRail />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <TopBar pageTitle={pageTitle} />
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
};
