import { Suspense, lazy, useState } from "react";
import { Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import WorkspaceBootstrap from "./components/WorkspaceBootstrap";
import WorkspaceSwitcher from "./components/WorkspaceSwitcher";

const Landing = lazy(() => import("./pages/Landing"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const FounderBrief = lazy(() => import("./pages/FounderBrief"));
const DecisionRegister = lazy(() => import("./pages/DecisionRegister"));
const Changes = lazy(() => import("./pages/Changes"));
const LaunchGuard = lazy(() => import("./pages/LaunchGuard"));
const Meetings = lazy(() => import("./pages/Meetings"));
const Engineering = lazy(() => import("./pages/Engineering"));
const Accuracy = lazy(() => import("./pages/Accuracy"));
const Models = lazy(() => import("./pages/Models"));
const Connectors = lazy(() => import("./pages/Connectors"));
const ConnectorRuns = lazy(() => import("./pages/ConnectorRuns"));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph"));
const ModelDetail = lazy(() => import("./pages/ModelDetail"));
const Query = lazy(() => import("./pages/Query"));
const ReviewQueue = lazy(() => import("./pages/ReviewQueue"));
const Sources = lazy(() => import("./pages/Sources"));

const ADMIN_NAV = [
  { to: "/app", label: "Dashboard", icon: BarChartIcon },
  { to: "/app/brief", label: "Founder Brief", icon: BriefIcon },
  { to: "/app/decisions", label: "Decision Register", icon: DecisionIcon },
  { to: "/app/changes", label: "What Changed", icon: ChangesIcon },
  { to: "/app/launch-guard", label: "Launch Guard", icon: GuardIcon },
  { to: "/app/meetings", label: "Meetings", icon: MeetingIcon },
  { to: "/app/engineering", label: "Engineering", icon: CodeIcon },
  { to: "/app/accuracy", label: "Accuracy", icon: GaugeIcon },
  { to: "/app/models", label: "Models", icon: CubeIcon },
  { to: "/app/query", label: "Query", icon: SearchIcon },
  { to: "/app/review", label: "Review Queue", icon: ShieldCheckIcon },
  { to: "/app/connectors", label: "Connectors", icon: PlugIcon },
  { to: "/app/sources", label: "Sources", icon: DocumentStackIcon },
  { to: "/app/graph", label: "Knowledge Graph", icon: GraphIcon },
];

function SidebarContent({ onNavigate }) {
  return (
    <>
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-800">
        <span className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
          CE
        </span>
        <span className="font-semibold text-white text-sm tracking-wide">
          Context Engine
        </span>
      </div>

      <nav className="flex-1 py-4 space-y-1 px-3">
        {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/app"}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-brand-600/20 text-brand-100 font-medium"
                  : "hover:bg-gray-800 hover:text-white"
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-gray-800 text-xs text-gray-500">
        v0.1.0 &middot; Admin
      </div>
    </>
  );
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader fullscreen />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app/*" element={<AdminShell />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function AdminShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  let pageTitle;
  const modelMatch = location.pathname.match(/^\/app\/model\/(.+)/);
  if (modelMatch) {
    pageTitle = "Model Detail";
  } else {
    pageTitle =
      ADMIN_NAV.find((n) =>
        n.to === "/app" ? location.pathname === "/app" : location.pathname.startsWith(n.to),
      )?.label ?? "Admin Dashboard";
  }

  return (
    <WorkspaceBootstrap>
      <div className="flex h-screen overflow-hidden">
        {/* ── Mobile overlay ──────────────────────── */}
        {mobileNavOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
        )}

        {/* ── Mobile drawer ───────────────────────── */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-60 flex flex-col bg-gray-900 text-gray-300 transform transition-transform duration-200 md:hidden ${
            mobileNavOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <SidebarContent onNavigate={() => setMobileNavOpen(false)} />
        </aside>

        {/* ── Desktop sidebar ─────────────────────── */}
        <aside className="hidden md:flex md:w-60 flex-col bg-gray-900 text-gray-300">
          <SidebarContent onNavigate={() => {}} />
        </aside>

        {/* ── Main area ───────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-14 border-b border-gray-200 bg-white flex items-center px-4 md:px-6 shrink-0 gap-3">
            <button
              className="md:hidden p-1.5 -ml-1 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation"
            >
              <HamburgerIcon className="w-5 h-5" />
            </button>
            <h1 className="text-sm font-semibold text-gray-700">{pageTitle}</h1>
            <div className="ml-auto">
              <WorkspaceSwitcher />
            </div>
          </header>

          <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route index element={<Dashboard />} />
                <Route path="brief" element={<FounderBrief />} />
                <Route path="decisions" element={<DecisionRegister />} />
                <Route path="changes" element={<Changes />} />
                <Route path="launch-guard" element={<LaunchGuard />} />
                <Route path="meetings" element={<Meetings />} />
                <Route path="meetings/:documentId" element={<Meetings />} />
                <Route path="engineering" element={<Engineering />} />
                <Route path="engineering/:documentId" element={<Engineering />} />
                <Route path="accuracy" element={<Accuracy />} />
                <Route path="models" element={<Models />} />
                <Route path="query" element={<Query />} />
                <Route path="review" element={<ReviewQueue />} />
                <Route path="review/:itemId" element={<ReviewQueue />} />
                <Route path="connectors" element={<Connectors />} />
                <Route path="connectors/:connectorType/runs" element={<ConnectorRuns />} />
                <Route path="sources" element={<Sources />} />
                <Route path="sources/:documentId" element={<Sources />} />
                <Route path="graph" element={<KnowledgeGraph />} />
                <Route path="model/:modelId" element={<ModelDetail />} />
                <Route path="*" element={<Navigate to="/app" replace />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </div>
    </WorkspaceBootstrap>
  );
}

function PageLoader({ fullscreen = false }) {
  return (
    <div
      className={
        fullscreen
          ? "min-h-screen bg-gray-50 flex items-center justify-center px-6"
          : "min-h-[240px] flex items-center justify-center rounded-xl border border-gray-200 bg-white px-6"
      }
    >
      <div className="text-center">
        <p className="text-sm font-medium text-gray-700">Loading page...</p>
        <p className="mt-1 text-xs text-gray-500">
          Pulling the next workflow view into the app shell.
        </p>
      </div>
    </div>
  );
}

/* ── Inline SVG icons (keeps deps minimal) ──────────────────── */

function BarChartIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4v9H3zm7-5h4v14h-4zm7-4h4v18h-4z" />
    </svg>
  );
}

function PlugIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2v4m-4-2h8m-6 4v4a2 2 0 002 2h0a2 2 0 002-2V8m-4 6v4m0 0H8m4 0h4" />
    </svg>
  );
}

function GaugeIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.93 19a10 10 0 1114.14 0H4.93z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 13l3-3" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 17h.01" />
    </svg>
  );
}

function CodeIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l-4 3 4 3M16 9l4 3-4 3M14 5l-4 14" />
    </svg>
  );
}

function GraphIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="5" cy="12" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path strokeLinecap="round" d="M7 11l10-4M7 13l10 4" />
    </svg>
  );
}

function SearchIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  );
}

function ShieldCheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l7 4v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V7l7-4z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4" />
    </svg>
  );
}

function CubeIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12" />
    </svg>
  );
}

function HamburgerIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function DocumentStackIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h8M8 11h8M8 15h5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 3h9a2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5a2 2 0 012-2z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 21h9a2 2 0 002-2V8" />
    </svg>
  );
}

function BriefIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 6h10M8 10h10M8 14h6" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 4h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z" />
    </svg>
  );
}

function DecisionIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 4h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z" />
    </svg>
  );
}

function ChangesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h8M8 12h8M8 17h5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h.01M4 12h.01M4 17h.01" />
    </svg>
  );
}

function GuardIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l7 4v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V7l7-4z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6" />
    </svg>
  );
}

function MeetingIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <rect x="4" y="6" width="12" height="10" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 10l4-2v6l-4-2" />
    </svg>
  );
}
