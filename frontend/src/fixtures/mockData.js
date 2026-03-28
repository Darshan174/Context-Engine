// ── Stat counters ──────────────────────────────────────────────
export const dashboardStats = [
  { label: "Sources", value: 12, icon: "database", delta: "+2 this week" },
  { label: "Models", value: 4, icon: "cube", delta: "stable" },
  { label: "Components", value: 347, icon: "puzzle", delta: "+18 this week" },
  { label: "Relationships", value: 1_203, icon: "link", delta: "+64 this week" },
];

// ── Recent activity ────────────────────────────────────────────
export const recentActivity = [
  { id: 1, text: "Slack connector synced 42 new messages", ts: "3 min ago", type: "sync" },
  { id: 2, text: "New component created: Q1 Revenue Model", ts: "18 min ago", type: "create" },
  { id: 3, text: "Relationship merged: OKR → Product Roadmap", ts: "1 hr ago", type: "merge" },
  { id: 4, text: "Stale alert: Google Drive token expiring", ts: "2 hr ago", type: "alert" },
  { id: 5, text: "Model retrained: Customer Health Score", ts: "5 hr ago", type: "model" },
  { id: 6, text: "Notion connector synced 8 pages", ts: "6 hr ago", type: "sync" },
];

// ── Stale alerts ───────────────────────────────────────────────
export const staleAlerts = [
  { id: 1, source: "Google Drive", message: "OAuth token expires in 2 days", severity: "warning" },
  { id: 2, source: "Gong", message: "No new data in 7 days", severity: "error" },
  { id: 3, source: "Slack #eng-alerts", message: "Channel archived — reconnect needed", severity: "error" },
];

// ── Connectors ─────────────────────────────────────────────────
export const connectors = [
  {
    id: "slack",
    name: "Slack",
    description: "Real-time messaging & channel history",
    status: "connected",
    lastSync: "3 min ago",
    itemsSynced: 14_820,
    color: "#4A154B",
  },
  {
    id: "notion",
    name: "Notion",
    description: "Wikis, docs & databases",
    status: "connected",
    lastSync: "6 hr ago",
    itemsSynced: 2_340,
    color: "#000000",
  },
  {
    id: "drive",
    name: "Google Drive",
    description: "Documents, sheets & slides",
    status: "warning",
    lastSync: "2 days ago",
    itemsSynced: 5_102,
    color: "#0F9D58",
  },
  {
    id: "gong",
    name: "Gong",
    description: "Call recordings & transcripts",
    status: "error",
    lastSync: "7 days ago",
    itemsSynced: 890,
    color: "#7C3AED",
  },
];

// ── Knowledge graph nodes & edges (placeholder) ────────────────
export const graphNodes = [
  { id: "n1", label: "Q1 Revenue Model", type: "model", x: 300, y: 200 },
  { id: "n2", label: "Customer Health Score", type: "model", x: 500, y: 120 },
  { id: "n3", label: "Slack #revenue", type: "source", x: 120, y: 300 },
  { id: "n4", label: "Product Roadmap", type: "component", x: 480, y: 340 },
  { id: "n5", label: "OKR Doc", type: "component", x: 200, y: 100 },
  { id: "n6", label: "Gong Calls", type: "source", x: 650, y: 260 },
  { id: "n7", label: "Churn Analysis", type: "component", x: 380, y: 420 },
];

export const graphEdges = [
  { source: "n3", target: "n1", label: "feeds" },
  { source: "n5", target: "n1", label: "informs" },
  { source: "n1", target: "n4", label: "drives" },
  { source: "n6", target: "n2", label: "feeds" },
  { source: "n2", target: "n7", label: "produces" },
  { source: "n4", target: "n7", label: "related" },
];

// ── Context Query — mock responses ─────────────────────────────
export const queryExamples = [
  {
    id: "q1",
    question: "What is our current MRR?",
    answer:
      "Monthly Recurring Revenue is currently $2.4M, up from $2.1M last quarter. This figure is sourced from the Stripe export and cross-referenced with the finance channel in Slack.",
    confidence: 0.94,
    components: [
      { id: "c1", name: "Monthly Recurring Revenue", value: "$2.4M", model: "Q1 Revenue Model" },
    ],
    sources: ["Stripe export", "Slack #finance"],
    answeredAt: "2 min ago",
  },
  {
    id: "q2",
    question: "How healthy are our customers?",
    answer:
      "Overall customer health is moderate. NPS is 62 (good), weekly active users are strong at 4,820, but support ticket volume is elevated at 38/week and onboarding time-to-value is 4.2 days which exceeds the 3-day target.",
    confidence: 0.87,
    components: [
      { id: "h1", name: "NPS Score", value: "62", model: "Customer Health Score" },
      { id: "h2", name: "Avg. Weekly Active Users", value: "4,820", model: "Customer Health Score" },
      { id: "h3", name: "Support Ticket Volume", value: "38/week", model: "Customer Health Score" },
      { id: "h4", name: "Time to Value (Onboarding)", value: "4.2 days", model: "Customer Health Score" },
    ],
    sources: ["Notion — CS tracker", "Analytics DB", "Zendesk export", "Gong transcripts"],
    answeredAt: "5 min ago",
  },
];

// ── Model detail — per-model data ──────────────────────────────
export const modelFixtures = {
  revenue: {
    name: "Q1 Revenue Model",
    description: "Composite model tracking revenue health across MRR, retention, pipeline, CAC, and churn.",
    lastUpdated: "2 hr ago",
    components: [
      {
        id: "c1",
        name: "Monthly Recurring Revenue",
        value: "$2.4M",
        confidence: 0.94,
        freshness: "2 hr ago",
        sources: ["Stripe export", "Slack #finance"],
      },
      {
        id: "c2",
        name: "Net Revenue Retention",
        value: "112%",
        confidence: 0.88,
        freshness: "1 day ago",
        sources: ["Notion — Metrics DB"],
      },
      {
        id: "c3",
        name: "Pipeline Coverage Ratio",
        value: "3.2x",
        confidence: 0.76,
        freshness: "3 days ago",
        sources: ["Gong transcripts", "Salesforce export"],
      },
      {
        id: "c4",
        name: "Customer Acquisition Cost",
        value: "$1,820",
        confidence: 0.91,
        freshness: "5 hr ago",
        sources: ["Google Drive — Finance folder"],
      },
      {
        id: "c5",
        name: "Logo Churn Rate",
        value: "3.1%",
        confidence: 0.82,
        freshness: "12 hr ago",
        sources: ["Stripe export", "Notion — CS tracker"],
      },
    ],
  },
  health: {
    name: "Customer Health Score",
    description: "Aggregated health signal combining usage, support, and NPS data.",
    lastUpdated: "5 hr ago",
    components: [
      {
        id: "h1",
        name: "NPS Score",
        value: "62",
        confidence: 0.91,
        freshness: "1 day ago",
        sources: ["Notion — CS tracker"],
      },
      {
        id: "h2",
        name: "Avg. Weekly Active Users",
        value: "4,820",
        confidence: 0.95,
        freshness: "3 hr ago",
        sources: ["Analytics DB", "Slack #product"],
      },
      {
        id: "h3",
        name: "Support Ticket Volume",
        value: "38/week",
        confidence: 0.89,
        freshness: "6 hr ago",
        sources: ["Zendesk export"],
      },
      {
        id: "h4",
        name: "Time to Value (Onboarding)",
        value: "4.2 days",
        confidence: 0.72,
        freshness: "5 days ago",
        sources: ["Gong transcripts", "Notion — Onboarding wiki"],
      },
    ],
  },
};
