import { Navigate, Route, Routes } from 'react-router-dom';

import { PlatformLayout } from './layouts/PlatformLayout';
import { ComingSoon } from './pages/ComingSoon';
import { ExperimentDetailPage } from './pages/ExperimentDetail';
import { ExperimentsPage } from './pages/Experiments';
import { OptimizationDetailPage } from './pages/OptimizationDetail';
import { OptimizationsPage } from './pages/Optimizations';
import { OverviewPage } from './pages/Overview';
import { ScenariosPage } from './pages/Scenarios';

export function App() {
  return (
    <Routes>
      <Route element={<PlatformLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="experiments/:experimentId" element={<ExperimentDetailPage />} />
        <Route path="optimizations" element={<OptimizationsPage />} />
        <Route path="optimizations/:optimizationId" element={<OptimizationDetailPage />} />
        <Route path="algorithms" element={<Navigate to="/optimizations" replace />} />
        <Route path="acceptance" element={<ComingSoon titleZh="验收中心" titleEn="Acceptance Center" />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
