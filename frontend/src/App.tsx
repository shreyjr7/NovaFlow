// src/App.tsx
import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home/Home";
import Fleet from "./pages/Fleet/Fleet";
import BusDetail from "./pages/BusDetail/BusDetail";
import RoadDefects from "./pages/RoadDefects/RoadDefects";
import Traffic from "./pages/Traffic/Traffic";
import Congestion from "./pages/Congestion/Congestion";
import PedestrianSafety from "./pages/PedestrianSafety/PedestrianSafety";
import Incidents from "./pages/Incidents/Incidents";
import ANPR from "./pages/ANPR/ANPR";
import OfflineBuffer from "./pages/OfflineBuffer/OfflineBuffer";
import GisCommandCenter from "./pages/GisCommandCenter/GisCommandCenter";
import OriginDestination from "./pages/OriginDestination/OriginDestination";
import RouteDelay from "./pages/RouteDelay/RouteDelay";
import Insights from "./pages/Insights/Insights";
import AlertCenter from "./pages/AlertCenter/AlertCenter";
import CameraHealth from "./pages/CameraHealth/CameraHealth";
import Privacy from "./pages/Privacy/Privacy";
import EvidenceCustody from "./pages/Evidence/EvidenceCustody";
import UrbanAnalytics from "./pages/UrbanAnalytics/UrbanAnalytics";
import ReportGenerator from "./pages/Reports/ReportGenerator";
import PublicDashboard from "./pages/Public/PublicDashboard";
import AdminPanel from "./pages/Admin/AdminPanel";
import AIModelManagement from "./pages/AIModels/AIModelManagement";
import GovernmentHeader from "./components/GovernmentHeader";
import UnifiedSidebar from "./components/UnifiedSidebar";
import TestingCenter from "./pages/Testing/TestingCenter";
import DemoFlowTheater from "./pages/DemoFlow/DemoFlowTheater";

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-white flex flex-col">
        <GovernmentHeader />
        <div className="flex flex-1 overflow-hidden">
          <UnifiedSidebar />
          <main className="flex-1 overflow-y-auto min-w-0">
            <Routes>
              <Route path="/" element={<Home />} />
        <Route path="/fleet" element={<Fleet />} />
        <Route path="/fleet/:busId" element={<BusDetail />} />
        <Route path="/road-defects" element={<RoadDefects />} />
        <Route path="/traffic" element={<Traffic />} />
        <Route path="/congestion" element={<Congestion />} />
        <Route path="/pedestrian-safety" element={<PedestrianSafety />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/anpr" element={<ANPR />} />
        <Route path="/offline-buffer" element={<OfflineBuffer />} />
        <Route path="/gis" element={<GisCommandCenter />} />
        <Route path="/command-center" element={<GisCommandCenter />} />
        <Route path="/od-analysis" element={<OriginDestination />} />
        <Route path="/route-delay" element={<RouteDelay />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/alerts" element={<AlertCenter />} />
        <Route path="/camera-health" element={<CameraHealth />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/evidence-custody" element={<EvidenceCustody />} />
        <Route path="/analytics-dashboard" element={<UrbanAnalytics />} />
        <Route path="/urban-analytics" element={<UrbanAnalytics />} />
        <Route path="/reports" element={<ReportGenerator />} />
        <Route path="/report-generator" element={<ReportGenerator />} />
        <Route path="/public" element={<PublicDashboard />} />
        <Route path="/citizen-portal" element={<PublicDashboard />} />
        <Route path="/public-dashboard" element={<PublicDashboard />} />
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="/admin-panel" element={<AdminPanel />} />
        <Route path="/ai-models" element={<AIModelManagement />} />
        <Route path="/models" element={<AIModelManagement />} />
        <Route path="/testing" element={<TestingCenter />} />
        <Route path="/test-center" element={<TestingCenter />} />
        <Route path="/demo" element={<DemoFlowTheater />} />
        <Route path="/demo-flow" element={<DemoFlowTheater />} />
        {/* Redirect any unknown path to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
