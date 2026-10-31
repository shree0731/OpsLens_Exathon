import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { LineagePage } from './pages/LineagePage';
import { PlaceholderPage } from './pages/PlaceholderPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/lineage" replace />} />
          
          <Route
            path="/lineage"
            element={
              <AppLayout pageTitle="Data Pipeline Lineage">
                <LineagePage />
              </AppLayout>
            }
          />

          <Route
            path="/timeline"
            element={
              <AppLayout pageTitle="Observability Timeline">
                <PlaceholderPage
                  title="Timeline View"
                  description="Chronological event log tracking pipeline stage runs, Sentinel checks, and alert lifecycle transitions."
                />
              </AppLayout>
            }
          />

          <Route
            path="/runs"
            element={
              <AppLayout pageTitle="Pipeline Runs">
                <PlaceholderPage
                  title="Pipeline Runs"
                  description="Detailed 5-stage pipeline run telemetry across 6 nightly jobs over 60 days."
                />
              </AppLayout>
            }
          />

          <Route
            path="/setup"
            element={
              <AppLayout pageTitle="Configuration & Setup">
                <PlaceholderPage
                  title="Engine Setup"
                  description="Reference clock watermarks, baseline management, and Exasol Personal Edition cluster connections."
                />
              </AppLayout>
            }
          />

          <Route
            path="/ask"
            element={
              <AppLayout pageTitle="Ask OpsLens">
                <PlaceholderPage
                  title="Ask OpsLens"
                  description="LLM-powered root cause analysis and natural language queries on pipeline telemetry."
                />
              </AppLayout>
            }
          />

          <Route
            path="/cost"
            element={
              <AppLayout pageTitle="Cost Radar">
                <PlaceholderPage
                  title="Workload Cost Radar"
                  description="Query telemetry, team cost attribution, and cold table scanner based on EXA_STATISTICS."
                />
              </AppLayout>
            }
          />

          <Route path="*" element={<Navigate to="/lineage" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
