import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  CircleDot,
  Copy,
  Database,
  ExternalLink,
  FileWarning,
  GitPullRequest,
  Lightbulb,
  Loader2,
  Minus,
  Plus,
  RefreshCw,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import {
  buildSessionKnowledgeMap,
  cardDisplayLine,
  cardDisplayText,
  formatTimeAgo,
  HEALTH_META,
  issueLabel,
  primarySourceUrl,
  pullRequestLabel,
  TONE_CLASSES,
} from "../digest";

const STAGE = { width: 3200, height: 2200 };
const MIN_ZOOM = 0.35;
const MAX_ZOOM = 2.2;
const DEFAULT_ZOOM = 0.64;
const DEFAULT_PAN = { x: 18, y: 24 };
const NODE_SIZE = {
  session: { width: 300, height: 104 },
  panel: { width: 420, height: 180 },
  wide: { width: 520, height: 190 },
  task: { width: 360, height: 112 },
};
const DEFAULT_POSITIONS = {
  "session-0": { x: 80, y: 190 },
  "session-1": { x: 80, y: 320 },
  "session-2": { x: 80, y: 450 },
  "session-3": { x: 80, y: 580 },
  decisions: { x: 460, y: 190 },
  blockers: { x: 460, y: 620 },
  prs: { x: 980, y: 190 },
  docs: { x: 980, y: 620 },
  issues: { x: 1500, y: 190 },
  task: { x: 1500, y: 620 },
};

const emptyAiSession = {
  id: "empty-ai-session",
  title: "AI session",
  summary: "No session imported yet",
  synthetic: true,
};

export default function DigestBoard({
  digest,
  workspaceName,
  generatedAt,
  onBuild,
  building = false,
  buildResult = null,
  buildError = null,
  onSelectCard,
}) {
  const boardRef = useRef(null);
  const panGestureRef = useRef(null);
  const pointersRef = useRef(new Map());
  const safariGestureRef = useRef(null);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const [pan, setPan] = useState(DEFAULT_PAN);
  const [positions, setPositions] = useState(DEFAULT_POSITIONS);
  const map = useMemo(
    () => buildSessionKnowledgeMap(digest, workspaceName),
    [digest, workspaceName],
  );
  const aiSessions = (map.aiSessions.length ? map.aiSessions : [emptyAiSession]).slice(0, 4);

  const moveNode = (nodeId, nextPosition) => {
    setPositions((current) => ({
      ...current,
      [nodeId]: normalizePosition(nextPosition),
    }));
  };

  const zoomAt = (nextZoomValue, clientPoint) => {
    const rect = boardRef.current?.getBoundingClientRect();
    const nextZoom = clampZoom(nextZoomValue);
    if (!rect || !clientPoint) {
      setZoom(nextZoom);
      return;
    }

    setPan((currentPan) => {
      const localX = clientPoint.x - rect.left;
      const localY = clientPoint.y - rect.top;
      const stageX = (localX - currentPan.x) / zoom;
      const stageY = (localY - currentPan.y) / zoom;
      return {
        x: localX - stageX * nextZoom,
        y: localY - stageY * nextZoom,
      };
    });
    setZoom(nextZoom);
  };

  const zoomFromCenter = (delta) => {
    const rect = boardRef.current?.getBoundingClientRect();
    zoomAt(roundZoom(zoom + delta), rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null);
  };

  const handleWheel = (event, { forceZoom = false, point = null } = {}) => {
    event.preventDefault();
    event.stopPropagation();
    if (forceZoom || event.ctrlKey || event.metaKey) {
      const factor = Math.exp(-event.deltaY * 0.006);
      zoomAt(zoom * factor, point || { x: event.clientX, y: event.clientY });
      return;
    }
    setPan((current) => ({
      x: current.x - event.deltaX,
      y: current.y - event.deltaY,
    }));
  };

  useEffect(() => {
    const board = boardRef.current;
    if (!board) return undefined;

    const eventTargetsBoard = (event) => {
      const target = event.target;
      return target instanceof Node && board.contains(target);
    };

    const preventViewportZoom = (event) => {
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
      }
    };

    const preventMultiTouchViewportZoom = (event) => {
      if (event.touches?.length > 1) {
        event.preventDefault();
      }
    };

    const onWheelCapture = (event) => {
      const isBoardEvent = eventTargetsBoard(event);
      if (!isBoardEvent) return;
      handleWheel(event);
    };

    const onGestureStart = (event) => {
      const isBoardEvent = eventTargetsBoard(event);
      if (!isBoardEvent) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const point = {
        x: event.clientX || board.getBoundingClientRect().left + board.clientWidth / 2,
        y: event.clientY || board.getBoundingClientRect().top + board.clientHeight / 2,
      };
      safariGestureRef.current = {
        zoom,
        x: point?.x || board.getBoundingClientRect().left + board.clientWidth / 2,
        y: point?.y || board.getBoundingClientRect().top + board.clientHeight / 2,
      };
    };

    const onGestureChange = (event) => {
      if (!eventTargetsBoard(event) && !safariGestureRef.current) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const gesture = safariGestureRef.current;
      if (!gesture) return;
      zoomAt(gesture.zoom * (event.scale || 1), { x: gesture.x, y: gesture.y });
    };

    const onGestureEnd = (event) => {
      if (!eventTargetsBoard(event) && !safariGestureRef.current) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      safariGestureRef.current = null;
    };

    window.addEventListener("wheel", preventViewportZoom, { capture: true, passive: false });
    window.addEventListener("touchmove", preventMultiTouchViewportZoom, { capture: true, passive: false });
    document.addEventListener("wheel", onWheelCapture, { capture: true, passive: false });
    document.addEventListener("gesturestart", onGestureStart, { capture: true, passive: false });
    document.addEventListener("gesturechange", onGestureChange, { capture: true, passive: false });
    document.addEventListener("gestureend", onGestureEnd, { capture: true, passive: false });

    return () => {
      window.removeEventListener("wheel", preventViewportZoom, { capture: true });
      window.removeEventListener("touchmove", preventMultiTouchViewportZoom, { capture: true });
      document.removeEventListener("wheel", onWheelCapture, { capture: true });
      document.removeEventListener("gesturestart", onGestureStart, { capture: true });
      document.removeEventListener("gesturechange", onGestureChange, { capture: true });
      document.removeEventListener("gestureend", onGestureEnd, { capture: true });
    };
  }, [zoom, pan]);

  const startPan = (event) => {
    if (event.button !== 0 || event.target.closest("[data-board-node], [data-no-pan]")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    panGestureRef.current = {
      mode: "pan",
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: pan.x,
      originY: pan.y,
    };
  };

  const movePan = (event) => {
    if (!pointersRef.current.has(event.pointerId)) return;
    pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const pointers = Array.from(pointersRef.current.values());

    if (pointers.length >= 2) {
      const [first, second] = pointers;
      const distance = pointerDistance(first, second);
      const center = pointerCenter(first, second);
      const rect = boardRef.current?.getBoundingClientRect();
      if (!rect || distance < 8) return;

      if (panGestureRef.current?.mode !== "pinch") {
        panGestureRef.current = {
          mode: "pinch",
          distance,
          zoom,
          stageX: (center.x - rect.left - pan.x) / zoom,
          stageY: (center.y - rect.top - pan.y) / zoom,
        };
      }

      const gesture = panGestureRef.current;
      const nextZoom = clampZoom((gesture.zoom * distance) / gesture.distance);
      setZoom(nextZoom);
      setPan({
        x: center.x - rect.left - gesture.stageX * nextZoom,
        y: center.y - rect.top - gesture.stageY * nextZoom,
      });
      return;
    }

    const gesture = panGestureRef.current;
    if (!gesture || gesture.mode !== "pan" || gesture.pointerId !== event.pointerId) return;
    setPan({
      x: gesture.originX + event.clientX - gesture.startX,
      y: gesture.originY + event.clientY - gesture.startY,
    });
  };

  const endPan = (event) => {
    pointersRef.current.delete(event.pointerId);
    if (!pointersRef.current.size || panGestureRef.current?.pointerId === event.pointerId) {
      panGestureRef.current = null;
    }
  };

  const copyPrompt = async () => {
    const copied = await copyText(map.nextAgentPrompt);
    if (copied) {
      setCopiedPrompt(true);
      window.setTimeout(() => setCopiedPrompt(false), 1600);
    }
  };

  const resetBoard = () => {
    setZoom(DEFAULT_ZOOM);
    setPan(DEFAULT_PAN);
    setPositions(DEFAULT_POSITIONS);
  };

  return (
    <section
      ref={boardRef}
      data-testid="session-knowledge-map"
      className="relative h-full min-h-[720px] overflow-hidden rounded-lg border border-slate-200/80 bg-[#f7f7f4] shadow-[0_24px_80px_rgba(15,23,42,0.08)] touch-none dark:border-white/[0.09] dark:bg-[#08090b]"
      style={{ overscrollBehavior: "contain", touchAction: "none", WebkitUserSelect: "none" }}
      onPointerDown={startPan}
      onPointerMove={movePan}
      onPointerUp={endPan}
      onPointerCancel={endPan}
    >
      <BoardDottedBackground />
      <BoardBrand
        workspaceName={workspaceName}
        health={digest?.health}
        generatedAt={generatedAt}
        onBuild={onBuild}
        building={building}
        buildResult={buildResult}
        buildError={buildError}
      />
      <div data-no-pan className="absolute right-4 top-4 z-30 flex items-center gap-1 rounded-lg border border-white/70 bg-white/72 p-1 shadow-[0_16px_45px_rgba(15,23,42,0.12)] backdrop-blur-xl dark:border-white/[0.12] dark:bg-black/50">
        <ToolButton label="Zoom out" onClick={() => zoomFromCenter(-0.1)}>
          <Minus className="h-4 w-4" />
        </ToolButton>
        <span className="min-w-12 text-center font-mono text-[11px] font-bold text-slate-600 dark:text-neutral-300">
          {Math.round(zoom * 100)}%
        </span>
        <ToolButton label="Zoom in" onClick={() => zoomFromCenter(0.1)}>
          <Plus className="h-4 w-4" />
        </ToolButton>
        <ToolButton label="Reset board" onClick={resetBoard}>
          <RotateCcw className="h-4 w-4" />
        </ToolButton>
      </div>

      <div className="h-full w-full cursor-grab overflow-hidden active:cursor-grabbing">
        <div
          className="relative origin-top-left"
          style={{
            width: STAGE.width,
            height: STAGE.height,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
          }}
        >
          <ComponentLines positions={positions} sessionCount={aiSessions.length} />

          {aiSessions.map((card, index) => (
            <DraggableFrame
              key={card.id}
              nodeId={`session-${index}`}
              position={positions[`session-${index}`]}
              size={NODE_SIZE.session}
              zoom={zoom}
              onMove={moveNode}
            >
              <MapNode
                icon={Bot}
                iconClassName="text-violet-600"
                title={index === 0 ? "AI session" : `AI session ${index + 1}`}
                primary={cardDisplayLine(card, "title", 7)}
                secondary={cardDisplayLine(card, "summary", 9)}
                onClick={card.synthetic ? undefined : () => onSelectCard?.(card)}
              />
            </DraggableFrame>
          ))}

          <DraggableFrame nodeId="decisions" position={positions.decisions} size={NODE_SIZE.wide} zoom={zoom} onMove={moveNode}>
            <PanelNode
              icon={Lightbulb}
              iconClassName="text-orange-600"
              title="Decisions"
              emptyText="No decisions captured yet"
              items={map.decisions}
              renderItem={(card) => cardDisplayText(card, "decision")}
              onItemClick={onSelectCard}
            />
          </DraggableFrame>

          <DraggableFrame nodeId="prs" position={positions.prs} size={NODE_SIZE.panel} zoom={zoom} onMove={moveNode}>
            <PanelNode
              icon={GitPullRequest}
              iconClassName="text-blue-600"
              title="PR"
              emptyText="No PRs linked yet"
              featured
              items={map.prs}
              renderItem={(card) => (
                <LinkedItem
                  label={pullRequestLabel(card)}
                  url={primarySourceUrl(card)}
                  detail={cardDisplayLine(card, "summary", 9)}
                />
              )}
              onItemClick={onSelectCard}
            />
          </DraggableFrame>

          <DraggableFrame nodeId="blockers" position={positions.blockers} size={NODE_SIZE.panel} zoom={zoom} onMove={moveNode}>
            <PanelNode
              icon={AlertTriangle}
              iconClassName="text-red-600"
              title="Blockers"
              emptyText="No blockers"
              items={map.blockers}
              renderItem={(card) => cardDisplayText(card, "blocker")}
              onItemClick={onSelectCard}
            />
          </DraggableFrame>

          <DraggableFrame nodeId="issues" position={positions.issues} size={NODE_SIZE.panel} zoom={zoom} onMove={moveNode}>
            <PanelNode
              icon={CircleDot}
              iconClassName="text-slate-600 dark:text-neutral-300"
              title="Issues"
              emptyText="No issues linked yet"
              items={map.issues}
              renderItem={(card) => (
                <LinkedItem
                  label={issueLabel(card)}
                  url={primarySourceUrl(card)}
                  detail={cardDisplayLine(card, "summary", 9)}
                />
              )}
              onItemClick={onSelectCard}
            />
          </DraggableFrame>

          <DraggableFrame nodeId="docs" position={positions.docs} size={NODE_SIZE.panel} zoom={zoom} onMove={moveNode}>
            <PanelNode
              icon={FileWarning}
              iconClassName="text-red-600"
              title="Broken docs"
              emptyText="No broken docs flagged"
              items={map.brokenDocs}
              renderItem={(card) => cardDisplayText(card, "docs")}
              onItemClick={onSelectCard}
            />
          </DraggableFrame>

          <DraggableFrame nodeId="task" position={positions.task} size={NODE_SIZE.task} zoom={zoom} onMove={moveNode}>
            <NextAgentTask
              prompt={map.nextAgentPrompt}
              copied={copiedPrompt}
              onCopy={copyPrompt}
            />
          </DraggableFrame>
        </div>
      </div>
    </section>
  );
}

function ComponentLines({ positions, sessionCount }) {
  const decisionTargets = Array.from({ length: sessionCount }, (_, index) => {
    const spacing = NODE_SIZE.wide.height / (sessionCount + 1);
    return sidePoint(positions.decisions, NODE_SIZE.wide, "left", spacing * (index + 1) - NODE_SIZE.wide.height / 2);
  });

  const lines = [
    ...Array.from({ length: sessionCount }, (_, index) => ({
      from: sidePoint(positions[`session-${index}`], NODE_SIZE.session, "right"),
      to: decisionTargets[index],
    })),
    {
      from: sidePoint(positions.decisions, NODE_SIZE.wide, "right", -42),
      to: sidePoint(positions.prs, NODE_SIZE.panel, "left", -42),
    },
    {
      from: sidePoint(positions.decisions, NODE_SIZE.wide, "bottom"),
      to: sidePoint(positions.blockers, NODE_SIZE.panel, "top"),
    },
    {
      from: sidePoint(positions.prs, NODE_SIZE.panel, "right", -40),
      to: sidePoint(positions.issues, NODE_SIZE.panel, "left", -40),
    },
    {
      from: sidePoint(positions.prs, NODE_SIZE.panel, "bottom"),
      to: sidePoint(positions.docs, NODE_SIZE.panel, "top"),
    },
    {
      from: sidePoint(positions.blockers, NODE_SIZE.panel, "right", 36),
      to: sidePoint(positions.docs, NODE_SIZE.panel, "left", 36),
    },
    {
      from: sidePoint(positions.docs, NODE_SIZE.panel, "right", 34),
      to: sidePoint(positions.task, NODE_SIZE.task, "left", 18),
    },
    {
      from: sidePoint(positions.issues, NODE_SIZE.panel, "bottom"),
      to: sidePoint(positions.task, NODE_SIZE.task, "top"),
    },
  ];

  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 overflow-visible"
      width={STAGE.width}
      height={STAGE.height}
      viewBox={`0 0 ${STAGE.width} ${STAGE.height}`}
    >
      <defs>
        <filter id="component-line-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {lines.map((line, index) => (
        <ComponentLine key={`${line.from.x}-${line.from.y}-${line.to.x}-${line.to.y}-${index}`} {...line} />
      ))}
    </svg>
  );
}

function ComponentLine({ from, to }) {
  const midX = Math.round((from.x + to.x) / 2);
  const path = `M ${from.x} ${from.y} H ${midX} V ${to.y} H ${to.x}`;

  return (
    <g data-component-line>
      <path
        d={path}
        fill="none"
        stroke="rgba(255,255,255,0.72)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#component-line-glow)"
      />
      <path
        d={path}
        fill="none"
        stroke="rgba(37,99,235,0.42)"
        strokeWidth="2.25"
        strokeDasharray="10 10"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={from.x} cy={from.y} r="4.5" fill="rgba(37,99,235,0.62)" />
      <circle cx={to.x} cy={to.y} r="4.5" fill="rgba(37,99,235,0.62)" />
    </g>
  );
}

function sidePoint(position, size, side, offset = 0) {
  const center = centerOf(position, size);
  if (side === "left") return { x: position.x, y: Math.round(center.y + offset) };
  if (side === "right") return { x: position.x + size.width, y: Math.round(center.y + offset) };
  if (side === "top") return { x: Math.round(center.x + offset), y: position.y };
  return { x: Math.round(center.x + offset), y: position.y + size.height };
}

function centerOf(position, size) {
  return {
    x: position.x + size.width / 2,
    y: position.y + size.height / 2,
  };
}

function BoardDottedBackground() {
  return (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 dark:hidden"
        style={{
          backgroundColor: "rgba(247, 247, 244, 1)",
          backgroundImage: "radial-gradient(circle, rgba(15, 23, 42, 0.18) 1.1px, transparent 1.1px)",
          backgroundSize: "32px 32px",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden dark:block"
        style={{
          backgroundColor: "rgba(8, 9, 11, 1)",
          backgroundImage: "radial-gradient(circle, rgba(148, 163, 184, 0.24) 1.1px, transparent 1.1px)",
          backgroundSize: "32px 32px",
        }}
      />
    </>
  );
}

function BoardBrand({
  workspaceName,
  health,
  generatedAt,
  onBuild,
  building,
  buildResult,
  buildError,
}) {
  const healthMeta = HEALTH_META[health?.status] || HEALTH_META.empty;
  const timestamp = buildResult?.finished_at || generatedAt;
  const timestampLabel = buildResult?.finished_at ? "Build checked" : "Digest refreshed";
  const buildNotice = buildResult ? buildResultNotice(buildResult) : null;
  const BuildNoticeIcon = buildNotice?.icon || CheckCircle2;

  return (
    <div
      data-no-pan
      className="absolute left-4 top-4 z-30 flex max-w-[760px] flex-col gap-2 rounded-lg border border-white/70 bg-white/72 px-4 py-3 shadow-[0_16px_45px_rgba(15,23,42,0.12)] backdrop-blur-xl dark:border-white/[0.12] dark:bg-black/50"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-black leading-5 text-slate-950 dark:text-white">Context Digest</span>
            <span className={`rounded-md border px-2 py-1 text-[11px] font-bold ${TONE_CLASSES[healthMeta.tone] || TONE_CLASSES.gray}`}>
              {healthMeta.label}
            </span>
          </span>
          <span className="mt-0.5 block truncate text-[11px] font-semibold leading-4 text-slate-500 dark:text-neutral-400">
            {timestampLabel}: {formatTimeAgo(timestamp)}
          </span>
        </span>
        <span className="flex shrink-0 flex-wrap items-center gap-2">
          <Link
            to="/app/sources"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-200 bg-white/80 px-3 text-xs font-bold text-slate-600 transition hover:bg-white dark:border-white/[0.1] dark:bg-white/[0.06] dark:text-neutral-300 dark:hover:bg-white/[0.1]"
          >
            <Database className="h-3.5 w-3.5" />
            Sources
          </Link>
          <button
            type="button"
            onClick={onBuild}
            disabled={building}
            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-slate-950 px-3 text-xs font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
          >
            {building ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Build Context
          </button>
        </span>
      </div>
      {buildNotice ? (
        <div className={`flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-[11px] font-bold ${TONE_CLASSES[buildNotice.tone] || TONE_CLASSES.gray}`}>
          <BuildNoticeIcon className="h-3.5 w-3.5" />
          {buildNotice.message}
        </div>
      ) : null}
      {buildError ? (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50/90 px-3 py-2 text-[11px] font-bold text-red-800 dark:border-red-900/60 dark:bg-red-950/35 dark:text-red-200">
          <AlertTriangle className="h-3.5 w-3.5" />
          {buildError?.message || "Build failed"}
        </div>
      ) : null}
    </div>
  );
}

function buildResultNotice(buildResult) {
  const docsPendingBefore = Number(buildResult.docs_pending_before ?? 0);
  const docsProcessed = Number(buildResult.docs_processed ?? 0);
  const componentsCreated = Number(buildResult.components_created ?? 0);
  const relationshipsInferred = Number(buildResult.relationships_inferred ?? 0);
  const totalComponents = Number(buildResult.stats?.total_components);

  if (
    docsPendingBefore === 0 &&
    docsProcessed === 0 &&
    componentsCreated === 0 &&
    relationshipsInferred === 0
  ) {
    return {
      icon: CircleDot,
      tone: "gray",
      message: Number.isFinite(totalComponents)
        ? `No pending docs to process · ${totalComponents} total components`
        : "No pending docs to process",
    };
  }

  return {
    icon: CheckCircle2,
    tone: buildResult.errors?.length ? "amber" : "green",
    message: `${docsProcessed} docs processed · ${componentsCreated} components created · ${relationshipsInferred} relationships inferred`,
  };
}

function DraggableFrame({ nodeId, position, size, zoom, onMove, children }) {
  const dragRef = useRef(null);

  const startDrag = (event) => {
    if (event.button !== 0 || event.target.closest("[data-no-drag]")) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: position.x,
      originY: position.y,
    };
  };

  const moveDrag = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.stopPropagation();
    onMove(nodeId, {
      x: drag.originX + (event.clientX - drag.startX) / zoom,
      y: drag.originY + (event.clientY - drag.startY) / zoom,
    });
  };

  const endDrag = (event) => {
    if (dragRef.current?.pointerId === event.pointerId) {
      event.stopPropagation();
      dragRef.current = null;
    }
  };

  return (
    <div
      data-board-node
      className="absolute z-10 cursor-grab touch-none active:cursor-grabbing"
      style={{ left: position.x, top: position.y, width: size.width, minHeight: size.height }}
      onPointerDown={startDrag}
      onPointerMove={moveDrag}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
    >
      {children}
    </div>
  );
}

function MapNode({ icon: Icon, iconClassName, title, primary, secondary, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex min-h-[104px] w-full items-center gap-4 rounded-lg border border-white/75 bg-white/82 px-5 py-4 text-left shadow-[0_18px_45px_rgba(15,23,42,0.12)] backdrop-blur-xl transition hover:border-slate-300 dark:border-white/[0.11] dark:bg-black/58"
    >
      <Icon className={`h-7 w-7 shrink-0 ${iconClassName}`} />
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-base font-black leading-6 text-slate-950 dark:text-white">{title}</p>
        </div>
        <p className="mt-1 truncate font-mono text-sm text-slate-900 dark:text-neutral-200">{primary}</p>
        {secondary ? (
          <p className="mt-1 line-clamp-1 text-xs font-semibold text-slate-500 dark:text-neutral-400">
            {secondary}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function PanelNode({
  icon: Icon,
  iconClassName,
  title,
  emptyText,
  items,
  renderItem,
  onItemClick,
  featured = false,
}) {
  return (
    <section
      className={`overflow-visible rounded-lg border bg-white/84 px-5 py-4 shadow-[0_18px_45px_rgba(15,23,42,0.12)] backdrop-blur-xl dark:bg-black/58 ${
        featured
          ? "border-blue-500/80 ring-4 ring-blue-500/10 dark:border-blue-400"
          : "border-white/75 dark:border-white/[0.11]"
      }`}
    >
      <div className="mb-3 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-200/80 bg-white/70 shadow-sm dark:border-white/[0.1] dark:bg-white/[0.06]">
          <Icon className={`h-5 w-5 ${iconClassName}`} />
        </span>
        <h2 className="text-base font-black leading-6 text-slate-950 dark:text-white">{title}</h2>
      </div>
      <div className="space-y-2">
        {items.length ? (
          items.slice(0, 5).map((card) => (
            <div
              key={card.id}
              role="button"
              tabIndex={0}
              onClick={() => onItemClick?.(card)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onItemClick?.(card);
                }
              }}
              className="block w-full whitespace-normal break-words rounded-md border border-slate-200/70 bg-white/55 px-3 py-2 text-left text-[13px] font-semibold leading-5 text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-white dark:border-white/[0.08] dark:bg-white/[0.045] dark:text-neutral-200 dark:hover:border-white/[0.15] dark:hover:bg-white/[0.075]"
            >
              {renderItem(card)}
            </div>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-slate-200 px-3 py-3 text-sm font-semibold text-slate-400 dark:border-neutral-800 dark:text-neutral-500">
            {emptyText}
          </p>
        )}
      </div>
    </section>
  );
}

function LinkedItem({ label, url, detail }) {
  return (
    <span className="block min-w-0">
      <span className="flex min-w-0 items-center gap-2">
        {url ? (
          <a
            data-no-drag
            href={url}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="min-w-0 truncate text-base font-black text-blue-700 underline-offset-2 hover:underline dark:text-blue-300"
          >
            {label}
          </a>
        ) : (
          <span className="min-w-0 truncate text-base font-black text-slate-950 dark:text-white">
            {label}
          </span>
        )}
        {url ? <ExternalLink className="h-3.5 w-3.5 shrink-0 text-blue-500" /> : null}
      </span>
      <span className="mt-1 block truncate font-mono text-xs text-slate-600 dark:text-neutral-400">
        {detail}
      </span>
    </span>
  );
}

function NextAgentTask({ prompt, copied, onCopy }) {
  return (
    <div
      data-testid="next-agent-task"
      className="group z-20 flex min-h-[112px] w-full flex-col rounded-lg border border-white/75 bg-white/84 px-5 py-4 text-left shadow-[0_18px_45px_rgba(15,23,42,0.12)] backdrop-blur-xl transition-all duration-200 hover:border-emerald-500 focus:border-emerald-500 focus:outline-none dark:border-white/[0.11] dark:bg-black/58"
    >
      <span className="flex items-center gap-3">
        <Sparkles className="h-7 w-7 shrink-0 text-emerald-600" />
        <span className="min-w-0">
          <span className="flex items-center gap-2 text-lg font-black leading-6 text-slate-950 dark:text-white">
            Next agent task
          </span>
          <button
            data-no-drag
            type="button"
            onClick={onCopy}
            className="mt-1 flex items-center gap-2 rounded-md text-sm font-semibold text-slate-500 transition hover:text-slate-950 dark:text-neutral-400 dark:hover:text-white"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Click to copy"}
          </button>
        </span>
      </span>
      <span className="mt-3 block max-h-0 overflow-hidden opacity-0 transition-all duration-200 group-hover:max-h-[520px] group-hover:opacity-100 group-focus:max-h-[520px] group-focus:opacity-100">
        <span className="mb-2 block text-xs font-bold uppercase text-slate-400">
          Handoff prompt
        </span>
        <span className="block max-h-[440px] overflow-y-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-700 dark:border-neutral-800 dark:bg-black dark:text-neutral-300">
          {prompt}
        </span>
      </span>
    </div>
  );
}

function ToolButton({ label, onClick, children }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-md text-slate-600 transition hover:bg-white hover:text-slate-950 dark:text-neutral-300 dark:hover:bg-white/[0.08] dark:hover:text-white"
    >
      {children}
    </button>
  );
}

function normalizePosition(position) {
  return {
    x: Math.round(Math.min(Math.max(-STAGE.width * 0.25, position.x), STAGE.width * 1.25)),
    y: Math.round(Math.min(Math.max(-STAGE.height * 0.25, position.y), STAGE.height * 1.25)),
  };
}

function clampZoom(value) {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, roundZoom(value)));
}

function pointerDistance(first, second) {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

function pointerCenter(first, second) {
  return {
    x: (first.x + second.x) / 2,
    y: (first.y + second.y) / 2,
  };
}

function roundZoom(value) {
  return Math.round(value * 100) / 100;
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // Fall back for browser contexts that block async clipboard writes.
    }
  }

  const textArea = document.createElement("textarea");
  textArea.value = value;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  textArea.style.top = "0";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  textArea.setSelectionRange(0, value.length);

  try {
    const didCopy = document.execCommand("copy");
    return didCopy || textArea.selectionStart === 0;
  } finally {
    document.body.removeChild(textArea);
  }
}
