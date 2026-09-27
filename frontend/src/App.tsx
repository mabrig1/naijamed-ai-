import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import { Spinner } from "./components/Layout";

// ── Lazy pages ───────────────────────────────────────────────────────────────

const Landing                   = lazy(() => import("./pages/Landing"));
const Login                     = lazy(() => import("./pages/Auth/Login"));
const Register                  = lazy(() => import("./pages/Auth/Register"));
const Dashboard                 = lazy(() => import("./pages/Dashboard"));
const ResearchStudio            = lazy(() => import("./pages/research/ResearchStudio"));
const BioinformaticsServices    = lazy(() => import("./pages/research/BioinformaticsServices"));
const Pricing                   = lazy(() => import("./pages/Pricing"));
const Formulary                 = lazy(() => import("./pages/Formulary"));
const FormularyPKPD             = lazy(() => import("./pages/FormularyPKPD"));
const FormularyPortfolio        = lazy(() => import("./pages/FormularyPortfolio"));
const FormularyPublicPortfolio  = lazy(() => import("./pages/FormularyPublicPortfolio"));
const FormularyAttestation      = lazy(() => import("./pages/FormularyAttestation"));
const FormularyCopilot          = lazy(() => import("./pages/FormularyCopilot"));
const FormularyJournalClub      = lazy(() => import("./pages/FormularyJournalClub"));
const FormularyJournalJoin      = lazy(() => import("./pages/FormularyJournalJoin"));
const FormularyGrantStudio      = lazy(() => import("./pages/FormularyGrantStudio"));
const MonetizationAdmin         = lazy(() => import("./pages/admin/MonetizationAdmin"));
const ResearchCommerceAdmin     = lazy(() => import("./pages/research/ResearchCommerceAdmin"));
const DiscoveryWorkbench        = lazy(() => import("./pages/discovery/DiscoveryWorkbench"));

const HerbList                  = lazy(() => import("./pages/Herbs/HerbList"));
const HerbDetail                = lazy(() => import("./pages/Herbs/HerbDetail"));
const HerbScan                  = lazy(() => import("./pages/Herbs/HerbScan"));

const FormulationList           = lazy(() => import("./pages/Formulation/FormulationList"));
const FormulationCreate         = lazy(() => import("./pages/Formulation/FormulationCreate"));
const FormulationDetail         = lazy(() => import("./pages/Formulation/FormulationDetail"));

const Marketplace               = lazy(() => import("./pages/Farming/Marketplace"));
const CreateListing             = lazy(() => import("./pages/Farming/CreateListing"));
const MarketDemand              = lazy(() => import("./pages/Farming/MarketDemand"));

const TrialList                 = lazy(() => import("./pages/Research/TrialList"));
const SubmitTrial               = lazy(() => import("./pages/Research/SubmitTrial"));
const HerbEvidence              = lazy(() => import("./pages/Research/HerbEvidence"));
const TrialDetail               = lazy(() => import("./pages/Research/TrialDetail"));

const DocumentList              = lazy(() => import("./pages/Compliance/DocumentList"));
const DocumentCreate            = lazy(() => import("./pages/Compliance/DocumentCreate"));
const DocumentDetail            = lazy(() => import("./pages/Compliance/DocumentDetail"));
const ComplianceChat            = lazy(() => import("./pages/Compliance/ComplianceChat"));

// ── Export Hub pages ─────────────────────────────────────────────────────────

const ExportMarketplace        = lazy(() => import("./pages/export/ExportMarketplace"));
const CreateExportListing      = lazy(() => import("./pages/export/CreateExportListing"));
const ExportListingDetail      = lazy(() => import("./pages/export/ExportListingDetail"));
const GlobalBuyerProfile       = lazy(() => import("./pages/export/GlobalBuyerProfile"));

const FreightQuoteCalculator   = lazy(() => import("./pages/logistics/FreightQuoteCalculator"));
const ShipmentTracker          = lazy(() => import("./pages/logistics/ShipmentTracker"));
const DocumentVault            = lazy(() => import("./pages/logistics/DocumentVault"));

const CustomsAssistant         = lazy(() => import("./pages/customs/CustomsAssistant"));
const PriceIntelligence        = lazy(() => import("./pages/prices/PriceIntelligence"));
const EscrowDashboard          = lazy(() => import("./pages/escrow/EscrowDashboard"));

// ── Helpers ───────────────────────────────────────────────────────────────────

function Loading() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Spinner />
    </div>
  );
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  return isAuthenticated
    ? <>{children}</>
    : <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/bioinformatics-services" element={<BioinformaticsServices />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/portfolio/:slug" element={<FormularyPublicPortfolio />} />
        <Route path="/formulary/attest/:token" element={<FormularyAttestation />} />
        <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />

        {/* Protected — all share the Layout shell */}
        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/research-studio" element={<ResearchStudio />} />
          <Route path="/formulary" element={<Formulary />} />
          <Route path="/formulary/pkpd" element={<FormularyPKPD />} />
          <Route path="/formulary/portfolio" element={<FormularyPortfolio />} />
          <Route path="/formulary/copilot" element={<FormularyCopilot />} />
          <Route path="/formulary/journal" element={<FormularyJournalClub />} />
          <Route path="/formulary/journal/join/:token" element={<FormularyJournalJoin />} />
          <Route path="/formulary/grants" element={<FormularyGrantStudio />} />
          <Route path="/research-commerce/admin" element={<ResearchCommerceAdmin />} />
          <Route path="/monetization/admin" element={<MonetizationAdmin />} />
          <Route path="/discovery" element={<DiscoveryWorkbench />} />

          {/* Herbs */}
          <Route path="/herbs" element={<HerbList />} />
          <Route path="/herbs/scan" element={<HerbScan />} />
          <Route path="/herbs/:id" element={<HerbDetail />} />

          {/* Formulations */}
          <Route path="/formulations" element={<FormulationList />} />
          <Route path="/formulations/create" element={<FormulationCreate />} />
          <Route path="/formulations/:id" element={<FormulationDetail />} />

          {/* Farming marketplace */}
          <Route path="/farming" element={<Marketplace />} />
          <Route path="/farming/create" element={<CreateListing />} />
          <Route path="/farming/demand" element={<MarketDemand />} />

          {/* Research */}
          <Route path="/research" element={<TrialList />} />
          <Route path="/research/submit" element={<SubmitTrial />} />
          <Route path="/research/evidence" element={<HerbEvidence />} />
          <Route path="/research/trials/:id" element={<TrialDetail />} />

          {/* Compliance */}
          <Route path="/compliance" element={<DocumentList />} />
          <Route path="/compliance/create" element={<DocumentCreate />} />
          <Route path="/compliance/chat" element={<ComplianceChat />} />
          <Route path="/compliance/:id" element={<DocumentDetail />} />

          {/* Export marketplace */}
          <Route path="/export" element={<ExportMarketplace />} />
          <Route path="/export/create" element={<CreateExportListing />} />
          <Route path="/export/listings/:id" element={<ExportListingDetail />} />
          <Route path="/export/buyers/register" element={<GlobalBuyerProfile />} />

          {/* Logistics */}
          <Route path="/logistics/freight" element={<FreightQuoteCalculator />} />
          <Route path="/logistics/tracker" element={<ShipmentTracker />} />
          <Route path="/logistics/documents" element={<DocumentVault />} />

          {/* Customs */}
          <Route path="/customs" element={<CustomsAssistant />} />

          {/* Price Intelligence */}
          <Route path="/prices" element={<PriceIntelligence />} />

          {/* Escrow */}
          <Route path="/escrow" element={<EscrowDashboard />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
