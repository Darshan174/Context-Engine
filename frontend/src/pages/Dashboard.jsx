import { Link } from "react-router-dom";
import { useDashboard } from "../api/hooks";
import StatusView from "../components/StatusView";

export default function Dashboard() {
  const query = useDashboard();

  if (query.isLoading || query.isError) {
    return (
      <div className="max-w-6xl mx-auto">
        <StatusView query={query} empty="No data yet. Create a workspace and add some models." />
      </div>
    );
  }

  const { stats = [], activity = [], alerts = [] } = query.data;
  const isEmpty = stats.length > 0 && stats.every((s) => s.value === 0);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Overview</h2>
        <p className="text-xs text-gray-400 mt-1">
          Your workspace at a glance — models, components, and data health.
        </p>
      </div>

      {/* ── Stat cards ──────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow"
          >
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value.toLocaleString()}</p>
            <p className="mt-1 text-xs text-gray-400">{s.delta}</p>
          </div>
        ))}
      </div>

      {isEmpty && (
        <div className="bg-brand-50 border border-brand-200 rounded-xl p-5 text-center">
          <p className="text-sm font-medium text-brand-800">Your workspace is empty</p>
          <p className="text-xs text-brand-600 mt-1">
            Head to{" "}
            <Link to="/models" className="underline font-medium">
              Models
            </Link>{" "}
            to create your first model and start adding components.
          </p>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* ── Recent activity ────────────────────── */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recent Activity</h3>
          {activity.length === 0 ? (
            <p className="text-sm text-gray-400">No recent activity.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {activity.map((a) => (
                <li key={a.id} className="py-3 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <ActivityDot type={a.type} />
                    <span className="text-sm text-gray-700">{a.text}</span>
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{a.ts}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* ── Stale alerts ───────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Stale Alerts</h3>
          {alerts.length === 0 ? (
            <p className="text-sm text-gray-400">No alerts.</p>
          ) : (
            <ul className="space-y-3">
              {alerts.map((a) => (
                <li
                  key={a.id}
                  className={`rounded-lg p-3 text-sm border ${
                    a.severity === "error"
                      ? "bg-red-50 border-red-200 text-red-800"
                      : "bg-amber-50 border-amber-200 text-amber-800"
                  }`}
                >
                  <p className="font-medium">{a.source}</p>
                  <p className="text-xs mt-0.5 opacity-80">{a.message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

const DOT_COLORS = {
  sync: "bg-blue-400",
  create: "bg-emerald-400",
  merge: "bg-brand-500",
  alert: "bg-amber-400",
  model: "bg-purple-400",
};

function ActivityDot({ type }) {
  return (
    <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${DOT_COLORS[type] || "bg-gray-300"}`} />
  );
}
