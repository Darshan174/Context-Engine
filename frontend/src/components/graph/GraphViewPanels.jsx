import { useRef } from "react";
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronRight,
  Copy,
  FileText,
  GitPullRequest,
  Layers3,
  Loader2,
  MessageCircle,
  MessageSquare,
  Network,
  Package,
  ShieldCheck,
  Sparkles,
  X as XIcon,
  XCircle,
  Zap,
} from "lucide-react";
import { sourceFamily } from "../../graph/sourceMetadata";

const SEV_DOT = { critical: "bg-red-500", high: "bg-amber-500", medium: "bg-yellow-400", low: "bg-slate-400" };
const SEV_PILL = {
  critical: "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400",
  high: "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400",
  medium: "bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400",
  low: "bg-slate-100 dark:bg-black text-slate-500",
};

export function GraphMinimap({ overview, onCenter, theme }) {
  const svgRef = useRef(null);
  if (!overview?.bounds || !overview.nodes?.length) return null;

  const width = 184;
  const height = 118;
  const padding = 10;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const scale = Math.min(usableWidth / overview.bounds.w, usableHeight / overview.bounds.h);
  const offsetX = padding + (usableWidth - overview.bounds.w * scale) / 2 - overview.bounds.x * scale;
  const offsetY = padding + (usableHeight - overview.bounds.h * scale) / 2 - overview.bounds.y * scale;
  const x = (value) => value * scale + offsetX;
  const y = (value) => value * scale + offsetY;
  const graphNodes = overview.nodes.filter((node) => node.type !== "model");
  const groupNodes = overview.nodes.filter((node) => node.type === "model");
  const viewport = overview.viewport
    ? {
      x: x(overview.viewport.x),
      y: y(overview.viewport.y),
      w: overview.viewport.w * scale,
      h: overview.viewport.h * scale,
    }
    : null;

  function handlePointerDown(event) {
    if (!svgRef.current || !onCenter) return;
    const rect = svgRef.current.getBoundingClientRect();
    const sx = ((event.clientX - rect.left) / rect.width) * width;
    const sy = ((event.clientY - rect.top) / rect.height) * height;
    onCenter({
      x: (sx - offsetX) / scale,
      y: (sy - offsetY) / scale,
    });
  }

  const isDark = theme === "dark";

  return (
    <div className="absolute bottom-20 right-4 z-20 rounded-xl border border-slate-200 bg-white/90 p-1.5 shadow-sm backdrop-blur-sm dark:border-neutral-800 dark:bg-black">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Graph minimap"
        onPointerDown={handlePointerDown}
        className="block cursor-crosshair rounded-lg"
      >
        <rect
          x="0"
          y="0"
          width={width}
          height={height}
          rx="8"
          fill={isDark ? "rgba(2,6,23,0.96)" : "rgba(248,250,252,0.96)"}
        />
        <pattern id="graph-minimap-grid" width="12" height="12" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.8" fill={isDark ? "rgba(148,163,184,0.28)" : "rgba(100,116,139,0.28)"} />
        </pattern>
        <rect x="0" y="0" width={width} height={height} rx="8" fill="url(#graph-minimap-grid)" />
        {groupNodes.map((node) => (
          <rect
            key={node.id}
            x={x(node.x)}
            y={y(node.y)}
            width={Math.max(8, node.w * scale)}
            height={Math.max(8, node.h * scale)}
            rx="4"
            fill="transparent"
            stroke={node.stroke}
            strokeWidth="1"
            opacity="0.28"
          />
        ))}
        {overview.edges.map((edge) => (
          <line
            key={edge.id}
            x1={x(edge.x1)}
            y1={y(edge.y1)}
            x2={x(edge.x2)}
            y2={y(edge.y2)}
            stroke={edge.color}
            strokeWidth="1"
            opacity="0.28"
          />
        ))}
        {graphNodes.map((node) => (
          <rect
            key={node.id}
            x={x(node.x)}
            y={y(node.y)}
            width={Math.max(node.type === "sourceHub" ? 7 : 4, node.w * scale)}
            height={Math.max(node.type === "sourceHub" ? 5 : 3, node.h * scale)}
            rx={node.type === "sourceHub" ? "2" : "1.5"}
            fill={node.fill}
            stroke={node.stroke}
            strokeWidth="1"
            opacity="0.82"
          />
        ))}
        {viewport && (
          <rect
            x={viewport.x}
            y={viewport.y}
            width={Math.max(12, viewport.w)}
            height={Math.max(10, viewport.h)}
            rx="3"
            fill="transparent"
            stroke={isDark ? "#f8fafc" : "#0f172a"}
            strokeWidth="1.5"
            opacity="0.9"
          />
        )}
      </svg>
    </div>
  );
}

export function GraphStat({ label, value, icon: Icon, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-700 dark:border-neutral-800 dark:bg-black dark:text-neutral-200",
    red: "border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300",
    amber: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300",
  };
  const iconClass = tone === "red" ? "text-red-500" : tone === "amber" ? "text-amber-500" : "text-slate-400";
  return (
    <div className={`flex min-h-11 items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 ${tones[tone] || tones.slate}`}>
      <div className="min-w-0">
        <p className="text-[9px] font-bold uppercase tracking-widest opacity-60">{label}</p>
        <p className="text-base font-black leading-tight">{value}</p>
      </div>
      {Icon ? <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} /> : <ShieldCheck className={`h-4 w-4 shrink-0 ${iconClass}`} />}
    </div>
  );
}

export function AgentsSidebarPanel({
  onClose,
  gapReport, gapLoading, gapError, onRunGaps,
  relReport, relLoading, relError, onRunRel,
  packResult, packLoading, packError, packCopied, selectedNode, onRunPack, onCopyPack,
}) {
  return (
    <div className="absolute bottom-3 right-3 top-20 z-40 flex w-[min(22rem,calc(100%-1.5rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-neutral-800 dark:bg-black">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-neutral-800 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-violet-500 flex items-center justify-center">
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-bold text-slate-900 dark:text-white">AI Agents</span>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-black transition-colors"
        >
          <XIcon className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <AgentRow
          icon={<Zap className="w-3.5 h-3.5" />}
          iconColor="bg-blue-500"
          num="01"
          title="Ingestion"
          desc="Slack · GitHub · Gmail → clean entities"
          action={
            <a href="/app/graph" className="text-[10px] font-bold text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-slate-200 border border-slate-200 dark:border-neutral-700 px-2 py-1 rounded-lg transition-colors whitespace-nowrap">
              Build Graph →
            </a>
          }
        />

        <AgentRow
          icon={<Network className="w-3.5 h-3.5" />}
          iconColor="bg-violet-500"
          num="02"
          title="Relationships"
          desc="Finds hidden links across all sources"
          action={
            <SidebarRunBtn loading={relLoading} onClick={onRunRel} color="violet">
              Run
            </SidebarRunBtn>
          }
        >
          {relError && <SidebarError>{relError}</SidebarError>}
          {relReport && (
            <div className="mt-2 space-y-1.5">
              <p className="text-[10px] text-slate-400">{relReport.message}</p>
              {relReport.suggested?.slice(0, 3).map((r, i) => (
                <div key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 dark:bg-black border border-slate-100 dark:border-neutral-800/50">
                  <span className={`text-[9px] font-bold px-1 rounded shrink-0 mt-0.5 ${r.confidence >= 0.7 ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400" : "bg-slate-100 dark:bg-black text-slate-500"}`}>
                    {Math.round(r.confidence * 100)}%
                  </span>
                  <p className="text-[10px] text-slate-600 dark:text-neutral-400 leading-snug">
                    <span className="font-semibold text-slate-700 dark:text-neutral-300">{r.source_name}</span>
                    <span className="text-slate-400 mx-1">→</span>
                    {r.target_name}
                  </p>
                </div>
              ))}
              {relReport.suggested?.length === 0 && relReport.duplicates?.length === 0 && (
                <p className="text-[10px] text-slate-400 italic text-center py-2">No hidden relationships found.</p>
              )}
            </div>
          )}
        </AgentRow>

        <div className="rounded-xl border-2 border-red-200 dark:border-red-900/60 overflow-hidden">
          <div className="px-3 py-2.5 bg-gradient-to-br from-red-50 to-orange-50/50 dark:from-red-950/40 dark:to-transparent border-b border-red-100 dark:border-red-900/40">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-5 h-5 rounded-md bg-red-500 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-3 h-3 text-white" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] font-bold text-red-500 dark:text-red-400 uppercase tracking-wide">03 · Killer Feature</span>
                  </div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white leading-none mt-0.5">Gap Detector</p>
                </div>
              </div>
              <SidebarRunBtn loading={gapLoading} onClick={onRunGaps} color="red">
                Run
              </SidebarRunBtn>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-neutral-400 mt-1.5 leading-relaxed">
              Scans the full graph — finds missing owners, blocked items, isolated nodes.
            </p>
          </div>
          {(gapError || gapReport) && (
            <div className="p-3 space-y-2">
              {gapError && <SidebarError>{gapError}</SidebarError>}
              {gapReport && <GapSidebarResult report={gapReport} />}
            </div>
          )}
        </div>

        <AgentRow
          icon={<MessageSquare className="w-3.5 h-3.5" />}
          iconColor="bg-brand-500"
          num="04"
          title="Ask AI"
          desc="Questions over the full graph with citations"
          action={
            <a href="/app/query" className="text-[10px] font-bold text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-slate-200 border border-slate-200 dark:border-neutral-700 px-2 py-1 rounded-lg transition-colors whitespace-nowrap">
              Open →
            </a>
          }
        />

        <AgentRow
          icon={<Package className="w-3.5 h-3.5" />}
          iconColor="bg-emerald-500"
          num="05"
          title="Context Pack"
          desc={selectedNode?.label ? "Selection + 1-hop neighbors" : "Generates a handoff prompt for AI agents"}
          action={
            <SidebarRunBtn loading={packLoading} onClick={onRunPack} color="emerald">
              {selectedNode?.id ? "Generate selected" : "Generate"}
            </SidebarRunBtn>
          }
        >
          {selectedNode?.label && (
            <div className="mt-2 rounded-lg border border-emerald-100 bg-emerald-50 px-2 py-1.5 text-[10px] text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300">
              Seed: {selectedNode.label}
            </div>
          )}
          {packError && <SidebarError>{packError}</SidebarError>}
          {packResult && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-[10px] text-slate-400">{packResult.entity_count} entities</p>
                <button
                  onClick={onCopyPack}
                  className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md transition-all ${packCopied ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400" : "bg-slate-100 dark:bg-black text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-600"}`}
                >
                  {packCopied ? <Check className="w-2.5 h-2.5" /> : <Copy className="w-2.5 h-2.5" />}
                  {packCopied ? "Copied!" : "Copy"}
                </button>
              </div>
              <pre className="text-[10px] text-slate-600 dark:text-neutral-300 bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono max-h-40 overflow-y-auto">
                {packResult.content}
              </pre>
            </div>
          )}
        </AgentRow>
      </div>
    </div>
  );
}

function AgentRow({ icon, iconColor, num, title, desc, action, children }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-neutral-800 bg-white dark:bg-black p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-5 h-5 rounded-md ${iconColor} flex items-center justify-center text-white shrink-0`}>
            {icon}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{num}</span>
              <span className="text-xs font-bold text-slate-800 dark:text-neutral-200">{title}</span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-neutral-400 leading-none mt-0.5 truncate">{desc}</p>
          </div>
        </div>
        <div className="shrink-0">{action}</div>
      </div>
      {children}
    </div>
  );
}

function SidebarRunBtn({ loading, onClick, color, children }) {
  const colors = {
    red: "bg-red-500 hover:bg-red-600",
    violet: "bg-violet-500 hover:bg-violet-600",
    emerald: "bg-emerald-500 hover:bg-emerald-600",
  };
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold text-white transition-colors disabled:opacity-60 shrink-0 ${colors[color] || "bg-brand-600 hover:bg-brand-500"}`}
    >
      {loading ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Sparkles className="w-2.5 h-2.5" />}
      {loading ? "…" : children}
    </button>
  );
}

function SidebarError({ children }) {
  return (
    <div className="mt-2 flex items-start gap-1.5 p-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40">
      <XCircle className="w-3 h-3 text-red-500 shrink-0 mt-0.5" />
      <p className="text-[10px] text-red-700 dark:text-red-400">{children}</p>
    </div>
  );
}

function GapSidebarResult({ report }) {
  const critical = report.gaps.filter(g => g.severity === "critical").length;
  const high = report.gaps.filter(g => g.severity === "high").length;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-1.5">
        {[
          { label: "Entities", value: report.stats.total_entities },
          { label: "Gaps", value: report.gaps.length, alert: critical + high > 0 },
          { label: "Isolated", value: report.stats.isolated, alert: report.stats.isolated > 0 },
        ].map(s => (
          <div key={s.label} className="rounded-lg bg-slate-50 dark:bg-black border border-slate-100 dark:border-neutral-800/50 p-2 text-center">
            <p className={`text-base font-bold ${s.alert ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-white"}`}>{s.value}</p>
            <p className="text-[9px] text-slate-400 uppercase tracking-wide">{s.label}</p>
          </div>
        ))}
      </div>

      {report.summary && (
        <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-800/30">
          <p className="text-[10px] text-amber-800 dark:text-amber-300 leading-relaxed">{report.summary}</p>
        </div>
      )}

      {report.gaps.slice(0, 4).map((g, i) => (
        <div key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 dark:bg-black border border-slate-100 dark:border-neutral-800/50">
          <div className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${SEV_DOT[g.severity] || SEV_DOT.low}`} />
          <div className="min-w-0">
            <div className="flex items-center gap-1 flex-wrap">
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${SEV_PILL[g.severity] || SEV_PILL.low}`}>{g.severity}</span>
            </div>
            <p className="text-[10px] font-semibold text-slate-700 dark:text-neutral-300 mt-0.5 leading-snug">{g.title}</p>
            {g.recommendation && (
              <p className="text-[10px] text-brand-600 dark:text-brand-400 mt-0.5 flex items-center gap-0.5">
                <ChevronRight className="w-2.5 h-2.5 shrink-0" />{g.recommendation}
              </p>
            )}
          </div>
        </div>
      ))}
      {report.gaps.length > 4 && (
        <p className="text-[10px] text-slate-400 text-center">+{report.gaps.length - 4} more gaps</p>
      )}
    </div>
  );
}

export function SourceCoveragePanel({ components }) {
  const byFamily = {};
  components.forEach((c) => {
    const family = sourceFamily(c);
    if (!byFamily[family]) byFamily[family] = { count: 0, types: new Set() };
    byFamily[family].count++;
    byFamily[family].types.add(c.source_type || "unknown");
  });

  const families = [
    { key: "github", label: "GitHub", icon: GitPullRequest, color: "text-slate-700 dark:text-neutral-300", bg: "bg-slate-100 dark:bg-black" },
    { key: "agent", label: "AI Sessions", icon: Bot, color: "text-violet-700 dark:text-violet-300", bg: "bg-violet-100 dark:bg-violet-900/30" },
    { key: "communication", label: "Comms", icon: MessageCircle, color: "text-sky-700 dark:text-sky-300", bg: "bg-sky-100 dark:bg-sky-900/30" },
    { key: "local", label: "Local", icon: FileText, color: "text-slate-600 dark:text-neutral-300", bg: "bg-slate-100 dark:bg-black" },
    { key: "other", label: "Other", icon: Layers3, color: "text-teal-700 dark:text-teal-300", bg: "bg-teal-100 dark:bg-teal-900/30" },
  ];

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">By source family</p>
      <div className="space-y-1.5">
        {families.map(({ key, label, icon: Icon, color, bg }) => {
          const data = byFamily[key];
          return (
            <div key={key} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-50 dark:bg-black border border-slate-100 dark:border-neutral-800/50">
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-md ${bg} flex items-center justify-center`}>
                  <Icon className={`w-3.5 h-3.5 ${color}`} />
                </div>
                <span className="text-xs font-bold text-slate-700 dark:text-neutral-300">{label}</span>
              </div>
              <span className="text-xs font-bold text-slate-500">{data ? data.count : 0}</span>
            </div>
          );
        })}
      </div>
      {components.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mt-3">By source type</p>
          <div className="space-y-1">
            {Object.entries(
              components.reduce((acc, c) => {
                const st = c.source_type || "unknown";
                acc[st] = (acc[st] || 0) + 1;
                return acc;
              }, {})
            )
              .sort((a, b) => b[1] - a[1])
              .slice(0, 8)
              .map(([type, count]) => (
                <div key={type} className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 dark:text-neutral-400 capitalize">{type.replace(/_/g, " ")}</span>
                  <span className="font-bold text-slate-700 dark:text-neutral-300">{count}</span>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

export function WorkLensPanel({ data, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
      </div>
    );
  }
  if (!data) {
    return <p className="text-xs text-slate-400 text-center py-4">Work lens unavailable.</p>;
  }

  const sections = [
    { key: "blockers", label: "Blockers", color: "red", icon: AlertTriangle },
    { key: "open_decisions", label: "Open Decisions", color: "amber", icon: ShieldCheck },
    { key: "active_tasks", label: "Active Tasks", color: "blue", icon: Zap },
    { key: "unresolved_questions", label: "Unresolved Questions", color: "sky", icon: MessageSquare },
    { key: "proposed_items", label: "Proposed", color: "violet", icon: Sparkles },
    { key: "stale_items", label: "Stale", color: "slate", icon: XCircle },
  ];

  return (
    <div className="space-y-3">
      {sections.map(({ key, label, color, icon: Icon }) => {
        const items = data[key] || [];
        const colorMap = {
          red: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
          amber: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
          blue: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
          sky: "bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400",
          violet: "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400",
          slate: "bg-slate-100 dark:bg-black text-slate-600 dark:text-neutral-300",
        };
        return (
          <div key={key}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                <Icon className="w-3 h-3 text-slate-400" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</span>
              </div>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${colorMap[color]}`}>{items.length}</span>
            </div>
            {items.length > 0 ? (
              <div className="space-y-1">
                {items.slice(0, 4).map((item) => (
                  <div key={item.id} className="p-2 rounded-lg bg-slate-50 dark:bg-black border border-slate-100 dark:border-neutral-800/50">
                    <p className="text-[11px] font-semibold text-slate-700 dark:text-neutral-300 truncate">{item.name || item.display_title}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {item.model_name && <span className="text-[9px] text-slate-400">{item.model_name}</span>}
                      {item.confidence != null && (
                        <span className={`text-[9px] font-bold ${item.confidence < 0.5 ? "text-red-500" : "text-slate-400"}`}>
                          {Math.round(item.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
                {items.length > 4 && (
                  <p className="text-[10px] text-slate-400 text-center">+{items.length - 4} more</p>
                )}
              </div>
            ) : (
              <p className="text-[10px] text-slate-400 italic">None</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
