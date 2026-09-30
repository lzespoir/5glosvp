import { Navigate, Route, Routes } from 'react-router-dom';

import { PlatformLayout } from './layouts/PlatformLayout';
import { AcceptancePage } from './pages/Acceptance';
import { BenchmarkCenterPage } from './pages/BenchmarkCenter';
import { BenchmarkDetailPage, BenchmarkRunDetailPage } from './pages/BenchmarkDetail';
import { ComparisonsPage } from './pages/Comparisons';
import { AlgorithmsPage } from './pages/Algorithms';
import { AlgorithmDetailPage } from './pages/Algorithms/AlgorithmDetail';
import { IntegrationGuidePage } from './pages/Algorithms/IntegrationGuide';
import { AlgorithmOnboardingPage } from './pages/AlgorithmOnboarding';
import { ExperimentDetailPage } from './pages/ExperimentDetail';
import { ExperimentsPage } from './pages/Experiments';
import { OptimizationDetailPage } from './pages/OptimizationDetail';
import { OptimizationsPage } from './pages/Optimizations';
import { OverviewPage } from './pages/Overview';
import { ScenariosPage } from './pages/Scenarios';
import { WorkspaceLibraryPage } from './pages/Scenarios/WorkspaceLibrary';
import { WorkspaceEditorPage } from './pages/Scenarios/WorkspaceEditor';
import { AntennaWorkspacePage } from './pages/Scenarios/AntennaWorkspacePage';
import { Day13Page } from './pages/Day13';
import { Day14Page } from './pages/Day14';
import { UserAssociationPage } from './pages/UserAssociation';
import { SystemPage } from './pages/System';
import { SystemExperimentDetailPage } from './pages/SystemExperimentDetail';
import { SystemOptimizationDetailPage } from './pages/SystemOptimizationDetail';
import { PlatformStatusPage } from './pages/PlatformStatus';

export function App() {
  return (
    <Routes>
      <Route element={<PlatformLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="platform-status" element={<PlatformStatusPage />} />
        <Route path="scenarios" element={<WorkspaceLibraryPage />} />
        <Route path="scenarios/advanced" element={<ScenariosPage />} />
        <Route path="scenarios/assets/antenna" element={<AntennaWorkspacePage />} />
        <Route path="scenarios/ue" element={<Day13Page />} />
        <Route path="scenarios/radio" element={<Day14Page />} />
        <Route path="scenarios/association" element={<UserAssociationPage />} />
        <Route path="scenarios/:scenarioId" element={<WorkspaceEditorPage />} />
        <Route path="a-matrix" element={<Navigate to="/scenarios/assets/antenna" replace />} />
        <Route path="ue-twin" element={<Navigate to="/scenarios/ue" replace />} />
        <Route path="radio-observability" element={<Navigate to="/scenarios/radio" replace />} />
        <Route path="user-association" element={<Navigate to="/scenarios/association" replace />} />
        <Route path="benchmarks" element={<BenchmarkCenterPage />} />
        <Route path="comparisons" element={<ComparisonsPage />} />
        <Route path="benchmarks/:benchmarkId/runs/:runId" element={<BenchmarkRunDetailPage />} />
        <Route path="benchmarks/:benchmarkId/:section" element={<BenchmarkDetailPage />} />
        <Route path="benchmarks/:benchmarkId" element={<BenchmarkDetailPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="experiments/:experimentId" element={<ExperimentDetailPage />} />
        <Route path="optimizations" element={<OptimizationsPage />} />
        <Route path="optimizations/:optimizationId" element={<OptimizationDetailPage />} />
        <Route path="optimizations/system/:optimizationId" element={<SystemOptimizationDetailPage />} />
        <Route path="system" element={<SystemPage />} />
        <Route path="system/experiments/:experimentId" element={<SystemExperimentDetailPage />} />
        <Route path="algorithms" element={<AlgorithmsPage />} />
        <Route path="algorithms/guide" element={<IntegrationGuidePage />} />
        <Route path="algorithm-onboarding" element={<AlgorithmOnboardingPage />} />
        <Route path="algorithms/:algorithmId" element={<AlgorithmDetailPage />} />
        <Route path="acceptance" element={<AcceptancePage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
