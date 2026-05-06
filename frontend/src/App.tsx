import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import { Spinner } from "./components/Layout";

// ── Lazy pages ───────────────────────────────────────────────────────────────
const Landing             = lazy(() => import("./pages/Landing"));
const Login               = lazy(() => import("./pages/Auth/Login"));
const Register            = lazy(() => import("./pages/Auth/Register"));
const Dashboard           = lazy(() => import("./pages/Dashboard"));
const HerbList            = lazy(() => import("./pages/Herbs/HerbList"));
const HerbDetail          = lazy(() => import("./pages/Herbs/HerbDetail"));
const HerbScan            = lazy(() => import("./pages/Herbs/HerbScan"));
const FormulationList     = lazy(() => import("./pages/Formulation/FormulationList"));
const FormulationCreate   = lazy(() => import("./pages/Formulation/FormulationCreate"));
const FormulationDetail   = lazy(() => import("./pages/Formulation/FormulationDetail"));
const Marketplace         = lazy(() => import("./pages/Farming/Marketplace"));
const CreateListing       = lazy(() => import("./pages/Farming/CreateListing"));
const MarketDemand        = lazy(() => import("./pages/Farming/MarketDemand"));
const TrialList           = lazy(() => import("./pages/Research/TrialList"));
const SubmitTrial         = lazy(() => import("./pages/Research/SubmitTrial"));
const HerbEvidence        = lazy(() => import("./pages/Research/HerbEvidence"));
const TrialDetail         = lazy(() => import("./pages/Research/TrialDetail"));
const DocumentList        = lazy(() => import("./pages/Compliance/DocumentList"));
const DocumentCreate      = lazy(() => import("./pages/Compliance/DocumentCreate"));
const DocumentDetail      = lazy(() => import("./pages/Compliance/DocumentDetail"));
const ComplianceChat      = lazy(() => import("./pages/Compliance/ComplianceChat"));

function Loading() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Spinner />
    </div>
  );
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login"    element={<PublicOnly><Login /></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />

        {/* Protected — all share the Layout shell */}
        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/dashboard"  element={<Dashboard />} />

          <Route path="/herbs"      element={<HerbList />} />
          <Route path="/herbs/scan" element={<HerbScan />} />
          <Route path="/herbs/:id"  element={<HerbDetail />} />

          <Route path="/formulations"          element={<FormulationList />} />
          <Route path="/formulations/create"   element={<FormulationCreate />} />
          <Route path="/formulations/:id"      element={<FormulationDetail />} />

          <Route path="/farming"               element={<Marketplace />} />
          <Route path="/farming/create"        element={<CreateListing />} />
          <Route path="/farming/demand"        element={<MarketDemand />} />

          <Route path="/research"              element={<TrialList />} />
          <Route path="/research/submit"       element={<SubmitTrial />} />
          <Route path="/research/evidence"     element={<HerbEvidence />} />
          <Route path="/research/trials/:id"   element={<TrialDetail />} />

          <Route path="/compliance"            element={<DocumentList />} />
          <Route path="/compliance/create"     element={<DocumentCreate />} />
          <Route path="/compliance/chat"       element={<ComplianceChat />} />
          <Route path="/compliance/:id"        element={<DocumentDetail />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
