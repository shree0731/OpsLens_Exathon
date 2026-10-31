import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  GitFork, 
  Clock, 
  PlayCircle, 
  Sliders, 
  HelpCircle, 
  DollarSign, 
  Layers
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Lineage', path: '/lineage', icon: <GitFork className="w-5 h-5" /> },
  { name: 'Timeline', path: '/timeline', icon: <Clock className="w-5 h-5" /> },
  { name: 'Runs', path: '/runs', icon: <PlayCircle className="w-5 h-5" /> },
  { name: 'Setup', path: '/setup', icon: <Sliders className="w-5 h-5" /> },
  { name: 'Ask', path: '/ask', icon: <HelpCircle className="w-5 h-5" /> },
  { name: 'Cost', path: '/cost', icon: <DollarSign className="w-5 h-5" /> },
];

export const LeftRail: React.FC = () => {
  return (
    <aside className="w-20 md:w-60 bg-white rounded-2xl border border-slate-200/80 shadow-soft flex flex-col justify-between py-6 px-3 my-4 ml-4 h-[calc(100vh-2rem)] flex-shrink-0">
      {/* Brand Header */}
      <div>
        <div className="flex items-center gap-3 px-3 py-2 mb-6">
          <div className="w-9 h-9 rounded-xl bg-navy-900 flex items-center justify-center text-white shadow-sm flex-shrink-0">
            <Layers className="w-5 h-5" />
          </div>
          <div className="hidden md:block">
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none">OpsLens</h1>
            <span className="text-[10px] font-semibold text-brand-600 uppercase tracking-wider">Exasol Observability</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-navy-900 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`
              }
            >
              <div className="flex-shrink-0">{item.icon}</div>
              <span className="hidden md:block">{item.name}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Exasol Native Indicator */}
      <div className="hidden md:block px-3 py-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">Exasol Engine</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Schema: <span className="font-mono text-slate-600">OPSLENS</span></p>
      </div>
    </aside>
  );
};
