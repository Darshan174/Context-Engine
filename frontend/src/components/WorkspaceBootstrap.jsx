import { useState } from "react";
import { useWorkspaces, useCreateWorkspace } from "../api/hooks";
import { useWorkspaceSelection } from "../context/WorkspaceContext";

/**
 * Full-screen gate shown when no workspace exists yet.
 * Renders children once at least one workspace is present.
 */
export default function WorkspaceBootstrap({ children }) {
  const { data: workspaces, isLoading, isError, error, refetch } = useWorkspaces();
  const create = useCreateWorkspace();
  const { setSelectedId } = useWorkspaceSelection();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // While checking, show a minimal loader
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-sm text-gray-400">Connecting to backend...</p>
      </div>
    );
  }

  if (isError) {
    // Network error (no HTTP status) — backend unreachable, let mock fallbacks work
    if (!error?.status) return children;

    // Real server error (4xx/5xx) — surface it instead of silently proceeding
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="w-full max-w-sm mx-4 text-center">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-3">
            <span className="text-red-500 text-lg font-bold">!</span>
          </div>
          <p className="text-sm font-medium text-red-600 mb-1">Failed to load workspaces</p>
          <p className="text-xs text-gray-400 mb-4">
            {error?.message || `Server returned ${error?.status}`}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Workspace exists — render app normally
  if (workspaces && workspaces.length > 0) return children;

  // No workspace — show creation form
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: (newWorkspace) => {
          if (newWorkspace?.id) setSelectedId(newWorkspace.id);
        },
      },
    );
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-md mx-4">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
          <div className="flex items-center gap-2 mb-6">
            <span className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
              CE
            </span>
            <span className="font-semibold text-gray-800 text-lg">Context Engine</span>
          </div>

          <h2 className="text-base font-semibold text-gray-800 mb-1">Create your workspace</h2>
          <p className="text-sm text-gray-500 mb-6">
            A workspace organizes your models, components, and data sources. You need at least one to get started.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. My Company"
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this workspace for?"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
              />
            </div>

            {create.isError && (
              <p className="text-xs text-red-600">
                {create.error?.message || "Failed to create workspace."}
              </p>
            )}

            <button
              type="submit"
              disabled={create.isPending || !name.trim()}
              className="w-full py-2.5 text-sm font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {create.isPending ? "Creating..." : "Create Workspace"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
