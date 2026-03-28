/**
 * Shared loading / error / empty-state overlay.
 *
 * Drop this at the top of any page that uses a React Query hook:
 *
 *   const q = useSomething();
 *   if (q.isLoading || q.isError || !q.data) return <StatusView query={q} empty="No items yet." />;
 */
export default function StatusView({ query, empty = "Nothing here yet." }) {
  if (query.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-400">
        <Spinner />
        <p className="mt-3 text-sm">Loading...</p>
      </div>
    );
  }

  if (query.isError) {
    const msg =
      query.error?.message || query.error?.detail || "Something went wrong.";
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-3">
          <span className="text-red-500 text-lg font-bold">!</span>
        </div>
        <p className="text-sm font-medium text-red-600">Failed to load</p>
        <p className="text-xs text-gray-400 mt-1 max-w-xs text-center">{msg}</p>
        <button
          onClick={() => query.refetch()}
          className="mt-4 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state — data loaded but nothing there
  const data = query.data;
  const isEmpty =
    data == null ||
    (Array.isArray(data) && data.length === 0) ||
    (typeof data === "object" && !Array.isArray(data) && Object.keys(data).length === 0);

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-400">
        <EmptyIcon />
        <p className="text-sm mt-3">{empty}</p>
      </div>
    );
  }

  return null; // data is ready — caller renders it
}

function Spinner() {
  return (
    <svg className="animate-spin h-6 w-6 text-brand-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function EmptyIcon() {
  return (
    <svg className="w-10 h-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
    </svg>
  );
}
