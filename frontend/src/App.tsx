import { Navigate, Route, Routes } from 'react-router-dom';

import { PlatformLayout } from './layouts/PlatformLayout';
import { ComingSoon } from './pages/ComingSoon';
import { ExperimentDetailPage } from './pages/ExperimentDetail';
import { ExperimentsPage } from './pages/Experiments';
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
        <Route path="algorithms" element={<ComingSoon titleZh="算法中心" titleEn="Algorithm Center" />} />
        <Route path="acceptance" element={<ComingSoon titleZh="验收中心" titleEn="Acceptance Center" />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
