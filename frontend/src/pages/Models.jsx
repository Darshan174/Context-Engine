import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useModels, useCreateModel } from "../api/hooks";
import StatusView from "../components/StatusView";

export default function Models() {
  const query = useModels();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);

  if (query.isLoading || query.isError) {
    return (
      <Wrapper onAdd={() => setShowForm(true)} showAdd={false}>
        <StatusView query={query} empty="No models yet. Create one to get started." />
      </Wrapper>
    );
  }

  if (!query.data?.length) {
    return (
      <Wrapper onAdd={() => setShowForm(true)} showAdd={!showForm}>
        {showForm
          ? <CreateModelForm onClose={() => setShowForm(false)} />
          : <StatusView query={query} empty="No models yet. Create one to get started." />}
      </Wrapper>
    );
  }

  return (
    <Wrapper onAdd={() => setShowForm(true)} showAdd={!showForm}>
      {showForm && <CreateModelForm onClose={() => setShowForm(false)} />}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {query.data.map((m) => (
          <button
            key={m.id}
            onClick={() => navigate(`/model/${m.id}`)}
            aria-label={`Open model ${m.name}`}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:shadow-md transition-shadow"
          >
            <h3 className="text-sm font-semibold text-gray-800">{m.name}</h3>
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{m.description || "No description"}</p>
            <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${m.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                {m.status}
              </span>
              <span>{new Date(m.updated_at).toLocaleDateString()}</span>
            </div>
          </button>
        ))}
      </div>
    </Wrapper>
  );
}

function Wrapper({ children, onAdd, showAdd }) {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Models</h2>
          <p className="text-xs text-gray-400 mt-1">
            A model groups related components into a structured view of your business.
          </p>
        </div>
        {showAdd && (
          <button
            onClick={onAdd}
            aria-label="Create new model"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
          >
            + New Model
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

function CreateModelForm({ onClose }) {
  const create = useCreateModel();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: (model) => {
          onClose();
          navigate(`/model/${model.id}`);
        },
      },
    );
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Create a new model</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor="model-name" className="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input
            id="model-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Q1 Revenue Model"
            required
            autoFocus
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          />
        </div>
        <div>
          <label htmlFor="model-description" className="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <input
            id="model-description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this model track?"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          />
        </div>
        {create.isError && (
          <p className="text-xs text-red-600">{create.error?.message || "Failed to create model."}</p>
        )}
        <div className="flex gap-2 pt-1">
          <button
            type="submit"
            disabled={create.isPending || !name.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {create.isPending ? "Creating..." : "Create"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
