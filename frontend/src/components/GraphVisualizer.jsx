const TYPE_COLORS = {
  model: { bg: "#eef2ff", border: "#6366f1", text: "#4338ca" },
  source: { bg: "#ecfdf5", border: "#10b981", text: "#065f46" },
  component: { bg: "#fefce8", border: "#eab308", text: "#854d0e" },
};

export default function GraphVisualizer({ nodes, edges }) {
  return (
    <div className="relative w-full h-full min-h-[420px] bg-white rounded-xl border border-gray-200 overflow-hidden">
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 800 500">
        {/* Edges */}
        {edges.map((edge) => {
          const src = nodes.find((n) => n.id === edge.source);
          const tgt = nodes.find((n) => n.id === edge.target);
          if (!src || !tgt) return null;
          const mx = (src.x + tgt.x) / 2;
          const my = (src.y + tgt.y) / 2;
          return (
            <g key={`${edge.source}-${edge.target}`}>
              <line
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke="#d1d5db"
                strokeWidth={1.5}
                strokeDasharray="6 3"
              />
              <text x={mx} y={my - 6} textAnchor="middle" className="text-[10px] fill-gray-400">
                {edge.label}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const palette = TYPE_COLORS[node.type] || TYPE_COLORS.component;
          return (
            <g key={node.id}>
              <rect
                x={node.x - 60}
                y={node.y - 18}
                width={120}
                height={36}
                rx={8}
                fill={palette.bg}
                stroke={palette.border}
                strokeWidth={1.5}
              />
              <text
                x={node.x}
                y={node.y + 4}
                textAnchor="middle"
                fill={palette.text}
                className="text-[11px] font-medium"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex gap-4 text-[11px] text-gray-500">
        {Object.entries(TYPE_COLORS).map(([type, palette]) => (
          <span key={type} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: palette.border }}
            />
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}
