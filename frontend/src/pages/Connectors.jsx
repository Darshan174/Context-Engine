import { useConnectors } from "../api/hooks";
import StatusView from "../components/StatusView";
import MockBadge from "../components/MockBadge";

const STATUS_PILL = {
  connected: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
};

const STATUS_LABEL = {
  connected: "Connected",
  warning: "Warning",
  error: "Error",
};

export default function Connectors() {
  const { data, isMock, ...query } = useConnectors();

  if (query.isLoading || query.isError || !data?.length) {
    return (
      <div className="max-w-5xl mx-auto">
        <StatusView query={{ data, ...query }} empty="No connectors configured." />
      </div>
    );
  }

  const list = data;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-800">Connectors</h2>
          {isMock && <MockBadge />}
        </div>
        <button className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors">
          + Add Connector
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        {list.map((c) => (
          <div
            key={c.id}
            className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-4 hover:shadow-sm transition-shadow"
          >
            {/* Header */}
            <div className="flex items-center gap-3">
              <span
                className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                style={{ backgroundColor: c.color }}
              >
                {c.name[0]}
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-gray-800">{c.name}</h3>
                <p className="text-xs text-gray-500 truncate">{c.description}</p>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium ${STATUS_PILL[c.status]}`}
              >
                {STATUS_LABEL[c.status]}
              </span>
            </div>

            {/* Meta */}
            <div className="grid grid-cols-2 text-xs text-gray-500 gap-y-1">
              <span>Last sync</span>
              <span className="text-right text-gray-700">{c.lastSync}</span>
              <span>Items synced</span>
              <span className="text-right text-gray-700">{c.itemsSynced.toLocaleString()}</span>
            </div>

            {/* Actions */}
            <div className="flex gap-2 mt-auto">
              <button className="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
                Configure
              </button>
              <button className="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors">
                Sync Now
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
