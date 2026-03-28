import { useState } from "react";
import { Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Models from "./pages/Models";
import Connectors from "./pages/Connectors";
import KnowledgeGraph from "./pages/KnowledgeGraph";
import ModelDetail from "./pages/ModelDetail";
import Query from "./pages/Query";
import WorkspaceBootstrap from "./components/WorkspaceBootstrap";
import WorkspaceSwitcher from "./components/WorkspaceSwitcher";

const NAV = [
  { to: "/", label: "Dashboard", icon: BarChartIcon },
  { to: "/models", label: "Models", icon: CubeIcon },
  { to: "/query", label: "Query", icon: SearchIcon },
  { to: "/connectors", label: "Connectors", icon: PlugIcon },
  { to: "/graph", label: "Knowledge Graph", icon: GraphIcon },
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
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  let pageTitle;
  const modelMatch = location.pathname.match(/^\/model\/(.+)/);
  if (modelMatch) {
    pageTitle = "Model Detail";
  } else {
    pageTitle =
      NAV.find((n) =>
        n.to === "/" ? location.pathname === "/" : location.pathname.startsWith(n.to),
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
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/models" element={<Models />} />
              <Route path="/query" element={<Query />} />
              <Route path="/connectors" element={<Connectors />} />
              <Route path="/graph" element={<KnowledgeGraph />} />
              <Route path="/model/:modelId" element={<ModelDetail />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </WorkspaceBootstrap>
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
