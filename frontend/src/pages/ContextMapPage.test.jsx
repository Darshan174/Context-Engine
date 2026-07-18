import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import ContextMapPage from "./ContextMapPage";

const mocks = vi.hoisted(() => ({
  workspaceId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  cardId: "component:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
}));

vi.mock("../api/hooks", () => ({
  useWorkspaces: () => ({ data: [{ id: mocks.workspaceId, name: "Context Engine" }], isLoading: false }),
}));

vi.mock("../context/WorkspaceContext", () => ({
  resolveWorkspaceId: () => mocks.workspaceId,
  useWorkspaceSelection: () => ({ selectedId: mocks.workspaceId, setSelectedId: vi.fn() }),
}));

vi.mock("../context-map/api", () => ({
  useContextDigest: () => ({
    data: {
      generated_at: "2026-07-18T08:00:00Z",
      cards: [{ id: mocks.cardId, title: "Inspect this exact risk", focus_eligible: false }],
      links: [],
      scope: {},
    },
    isLoading: false,
    isError: false,
  }),
  useBuildContext: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useIndexProject: () => ({ isPending: false, isError: false, mutate: vi.fn(), mutateAsync: vi.fn() }),
  usePrepareContext: () => ({ isPending: false, isError: false, mutateAsync: vi.fn() }),
  useRunTimeline: () => ({ data: null, isLoading: false, isError: false, refetch: vi.fn() }),
  useOpenLoops: () => ({ data: null, isLoading: false, isError: false }),
  usePlaybooks: () => ({ data: null, isLoading: false }),
  useUpdateOpenLoop: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useUpdatePlaybook: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("../context-map/components/DigestBoard", () => ({
  default: () => <div>Digest board</div>,
}));

vi.mock("../context-map/components/ContextInspector", () => ({
  default: ({ card }) => <div role="dialog" aria-label="Context evidence inspector"><h2>{card.title}</h2></div>,
}));

vi.mock("../context-map/components/OpenLoopsPanel", () => ({
  default: () => <div>Open loops</div>,
}));

describe("ContextMapPage deep links", () => {
  it("opens the exact digest card requested by Now or the work queue", async () => {
    render(
      <MemoryRouter initialEntries={[`/app/explain?card=${encodeURIComponent(mocks.cardId)}`]}>
        <ContextMapPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("dialog", { name: "Context evidence inspector" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inspect this exact risk" })).toBeInTheDocument();
  });
});
