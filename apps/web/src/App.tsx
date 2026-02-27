import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { AlertsPage } from "./pages/AlertsPage";
import { AlertDetailPage } from "./pages/AlertDetailPage";
import { DebugPage } from "./pages/DebugPage";
import { InvestigationCasesPage } from "./pages/InvestigationCasesPage";
import { ResolvedCasesPage } from "./pages/ResolvedCasesPage";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <div className="card topbar topbar-modern">
        <div className="container topbar-layout">
          <div className="topbar-brand">
            <strong className="brand">SafeLink Monitor</strong>
            <div className="muted topbar-subtitle">AI-assisted harmful content response</div>
          </div>
          <div className="topbar-nav-groups">
            <div className="nav-group">
              <span className="nav-group-label">Cases</span>
              <NavLink to="/alerts" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                Dashboard
              </NavLink>
              <NavLink to="/cases/investigating" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                Investigating
              </NavLink>
              <NavLink to="/cases/resolved" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                Resolved
              </NavLink>
            </div>
            <div className="nav-group">
              <span className="nav-group-label">Admin</span>
              <NavLink to="/debug" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                Debug
              </NavLink>
            </div>
          </div>
        </div>
      </div>
      <div className="container">{children}</div>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route
        path="/alerts"
        element={
          <Layout>
            <AlertsPage />
          </Layout>
        }
      />
      <Route
        path="/alerts/:id"
        element={
          <Layout>
            <AlertDetailPage />
          </Layout>
        }
      />
      <Route
        path="/cases/investigating"
        element={
          <Layout>
            <InvestigationCasesPage />
          </Layout>
        }
      />
      <Route
        path="/cases/resolved"
        element={
          <Layout>
            <ResolvedCasesPage />
          </Layout>
        }
      />
      <Route
        path="/debug"
        element={
          <Layout>
            <DebugPage />
          </Layout>
        }
      />
      <Route path="*" element={<Navigate to="/alerts" />} />
    </Routes>
  );
}
