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

// ── Source documents ───────────────────────────────────────────
export const sourceDocuments = [
  {
    id: "sd1",
    connectorType: "slack",
    externalId: "C-price:1711699200.000100",
    author: "Alice Chen",
    content: "decision: enterprise pricing moves to $600/seat starting next quarter",
    sourceUrl: "https://slack.com/archives/C-price/p1711699200000100",
    createdAtSource: "2026-03-29T09:20:00Z",
    ingestedAt: "2026-03-29T09:22:00Z",
    processedAt: "2026-03-29T09:23:00Z",
    metadata: { channel_name: "pricing", location: "#pricing" },
  },
  {
    id: "sd2",
    connectorType: "slack",
    externalId: "C-prod:1711702800.000200",
    author: "Rahul Verma",
    content: "blocker: SSO rollout is blocked by audit review and enterprise procurement timing",
    sourceUrl: "https://slack.com/archives/C-prod/p1711702800000200",
    createdAtSource: "2026-03-29T10:20:00Z",
    ingestedAt: "2026-03-29T10:21:00Z",
    processedAt: null,
    metadata: { channel_name: "product", location: "#product" },
  },
  {
    id: "sd3",
    connectorType: "notion",
    externalId: "notion:page-abc-123",
    author: "alice@example.com",
    content: "Engineering Roadmap\n\nWe are targeting Q3 for the SSO launch.\n\n# Key Decisions\n\n- Adopt SAML over OIDC",
    sourceUrl: "https://notion.so/eng-roadmap-abc123",
    createdAtSource: "2026-03-28T10:00:00Z",
    ingestedAt: "2026-03-29T14:05:00Z",
    processedAt: "2026-03-29T14:06:00Z",
    metadata: { page_id: "page-abc-123", location: "Engineering Roadmap" },
  },
  {
    id: "sd4",
    connectorType: "notion",
    externalId: "notion:page-pricing-456",
    author: "bob@example.com",
    content: "Pricing Strategy\n\naction item: update enterprise packaging copy before launch",
    sourceUrl: "https://notion.so/pricing-strategy-456",
    createdAtSource: "2026-03-29T12:30:00Z",
    ingestedAt: "2026-03-29T14:07:00Z",
    processedAt: null,
    metadata: { page_id: "page-pricing-456", location: "Pricing Strategy" },
  },
  {
    id: "sd5",
    connectorType: "slack",
    externalId: "C-finance:1711710000.000300",
    author: "Dana Singh",
    content: "decision: monthly recurring revenue closed at $2.4M after the March Stripe reconciliation",
    sourceUrl: "https://slack.com/archives/C-finance/p1711710000000300",
    createdAtSource: "2026-03-29T12:20:00Z",
    ingestedAt: "2026-03-29T12:21:00Z",
    processedAt: "2026-03-29T12:23:00Z",
    metadata: { channel_name: "finance", location: "#finance" },
  },
  {
    id: "sd6",
    connectorType: "notion",
    externalId: "notion:page-metrics-789",
    author: "finance@example.com",
    content: "Metrics DB\n\nNet revenue retention is holding at 112% for the current quarter.",
    sourceUrl: "https://notion.so/metrics-db-789",
    createdAtSource: "2026-03-29T11:10:00Z",
    ingestedAt: "2026-03-29T12:30:00Z",
    processedAt: "2026-03-29T12:32:00Z",
    metadata: { page_id: "page-metrics-789", location: "Metrics DB" },
  },
  {
    id: "sd7",
    connectorType: "notion",
    externalId: "notion:page-cs-101",
    author: "cs@example.com",
    content: "CS tracker\n\nNPS is 62 and time to value is averaging 4.2 days this week.",
    sourceUrl: "https://notion.so/cs-tracker-101",
    createdAtSource: "2026-03-29T08:45:00Z",
    ingestedAt: "2026-03-29T13:10:00Z",
    processedAt: "2026-03-29T13:12:00Z",
    metadata: { page_id: "page-cs-101", location: "CS tracker" },
  },
  {
    id: "sd8",
    connectorType: "slack",
    externalId: "C-product:1711713600.000400",
    author: "Maya Patel",
    content: "discussion: weekly active users are at 4,820 after the new onboarding flow rollout",
    sourceUrl: "https://slack.com/archives/C-product/p1711713600000400",
    createdAtSource: "2026-03-29T13:20:00Z",
    ingestedAt: "2026-03-29T13:21:00Z",
    processedAt: "2026-03-29T13:23:00Z",
    metadata: { channel_name: "product", location: "#product" },
  },
  {
    id: "sd9",
    connectorType: "gong",
    externalId: "gong:call-555",
    author: "Customer Call Bot",
    content: "discussion: onboarding time to value is still above target and support volume remains elevated",
    sourceUrl: "https://app.gong.io/call/555",
    createdAtSource: "2026-03-28T17:15:00Z",
    ingestedAt: "2026-03-29T13:40:00Z",
    processedAt: "2026-03-29T13:42:00Z",
    metadata: { location: "Gong Q1 onboarding review" },
  },
];

// ── Review queue ───────────────────────────────────────────────
export const reviewQueue = [
  {
    id: "rq1",
    status: "needs_review",
    severity: "high",
    kind: "conflict",
    title: "Enterprise pricing changed across Slack and Notion",
    summary:
      "Slack indicates $600/seat next quarter, while the pricing page draft still references $500/seat.",
    confidence: 0.58,
    freshness: "2 hr ago",
    model: "Pricing Strategy",
    modelId: "pricing",
    sources: ["Slack #pricing", "Notion Pricing Strategy"],
    sourceDocuments: [
      { id: "sd1", label: "#pricing enterprise decision", connectorType: "slack" },
      { id: "sd4", label: "Pricing strategy page", connectorType: "notion" },
    ],
    rationale:
      "Two high-authority sources disagree on the current enterprise pricing decision. This should be resolved before external-facing docs or AI answers rely on it.",
    suggestedAction: "Choose the approved value and mark the superseded source.",
  },
  {
    id: "rq2",
    status: "needs_review",
    severity: "medium",
    kind: "low_confidence",
    title: "SSO launch blocker extracted with low confidence",
    summary:
      "The ingestion pipeline found a blocker tied to audit review, but the wording is still ambiguous between procurement and security dependency.",
    confidence: 0.44,
    freshness: "5 hr ago",
    model: "Engineering Roadmap",
    modelId: "roadmap",
    sources: ["Slack #product", "Notion Engineering Roadmap"],
    sourceDocuments: [
      { id: "sd2", label: "#product SSO blocker thread", connectorType: "slack" },
      { id: "sd3", label: "Engineering Roadmap", connectorType: "notion" },
    ],
    rationale:
      "The same topic appears in multiple places, but the extracted blocker relationship needs a human to confirm the exact cause.",
    suggestedAction: "Confirm whether audit review or procurement timing is the canonical blocker.",
  },
  {
    id: "rq3",
    status: "approved",
    severity: "low",
    kind: "fact_update",
    title: "Roadmap decision approved for Q3",
    summary:
      "The Q3 SSO target has already been approved and is now part of the active company context.",
    confidence: 0.92,
    freshness: "1 day ago",
    model: "Engineering Roadmap",
    modelId: "roadmap",
    sources: ["Notion Engineering Roadmap"],
    sourceDocuments: [
      { id: "sd3", label: "Engineering Roadmap", connectorType: "notion" },
    ],
    rationale:
      "This item already has clear supporting evidence and no contradictions.",
    suggestedAction: "No action needed.",
  },
  {
    id: "rq4",
    status: "superseded",
    severity: "medium",
    kind: "superseded_fact",
    title: "Old pricing guidance still appears in historical notes",
    summary:
      "A prior pricing note remains in historical Slack context but has been superseded by the newer pricing decision.",
    confidence: 0.89,
    freshness: "3 days ago",
    model: "Pricing Strategy",
    modelId: "pricing",
    sources: ["Slack #finance archive"],
    sourceDocuments: [
      { id: "sd1", label: "#pricing enterprise decision", connectorType: "slack" },
    ],
    rationale:
      "The system preserved the old fact for time-travel context, but it should not be treated as current truth.",
    suggestedAction: "No action needed unless the old note is still being cited in active workflows.",
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
      {
        id: "c1",
        name: "Monthly Recurring Revenue",
        value: "$2.4M",
        model: "Q1 Revenue Model",
        sourceDocuments: [
          { id: "sd5", label: "#finance revenue decision", connectorType: "slack" },
        ],
      },
    ],
    sources: ["Stripe export", "Slack #finance"],
    sourceDocuments: [
      { id: "sd5", label: "#finance revenue decision", connectorType: "slack" },
    ],
    reviewStatus: "approved",
    answeredAt: "2 min ago",
  },
  {
    id: "q2",
    question: "How healthy are our customers?",
    answer:
      "Overall customer health is moderate. NPS is 62 (good), weekly active users are strong at 4,820, but support ticket volume is elevated at 38/week and onboarding time-to-value is 4.2 days which exceeds the 3-day target.",
    confidence: 0.87,
    components: [
      {
        id: "h1",
        name: "NPS Score",
        value: "62",
        model: "Customer Health Score",
        sourceDocuments: [{ id: "sd7", label: "CS tracker", connectorType: "notion" }],
      },
      {
        id: "h2",
        name: "Avg. Weekly Active Users",
        value: "4,820",
        model: "Customer Health Score",
        sourceDocuments: [{ id: "sd8", label: "#product usage update", connectorType: "slack" }],
      },
      {
        id: "h3",
        name: "Support Ticket Volume",
        value: "38/week",
        model: "Customer Health Score",
        sourceDocuments: [{ id: "sd9", label: "Gong onboarding review", connectorType: "gong" }],
      },
      {
        id: "h4",
        name: "Time to Value (Onboarding)",
        value: "4.2 days",
        model: "Customer Health Score",
        sourceDocuments: [{ id: "sd7", label: "CS tracker", connectorType: "notion" }],
      },
    ],
    sources: ["Notion — CS tracker", "Analytics DB", "Zendesk export", "Gong transcripts"],
    sourceDocuments: [
      { id: "sd7", label: "CS tracker", connectorType: "notion" },
      { id: "sd8", label: "#product usage update", connectorType: "slack" },
      { id: "sd9", label: "Gong onboarding review", connectorType: "gong" },
    ],
    reviewStatus: "needs_review",
    reviewItemId: "rq2",
    reviewSummary:
      "Support and onboarding signals still need a human pass because recent Gong notes and the CS tracker are not fully aligned.",
    answeredAt: "5 min ago",
  },
];

// ── Model detail — per-model data ──────────────────────────────
export const modelFixtures = {
  pricing: {
    name: "Pricing Strategy",
    description: "Current pricing decisions, packaging changes, and launch dependencies.",
    lastUpdated: "2 hr ago",
    components: [
      {
        id: "p1",
        name: "Enterprise Seat Price",
        value: "$600/seat",
        confidence: 0.86,
        freshness: "2 hr ago",
        sources: ["Slack #pricing", "Notion Pricing Strategy"],
        reviewStatus: "needs_review",
        reviewItemId: "rq1",
        reviewSummary: "Slack and Notion disagree on the active enterprise price. Resolve before external use.",
        sourceDocuments: [
          { id: "sd1", label: "#pricing enterprise decision", connectorType: "slack" },
          { id: "sd4", label: "Pricing strategy page", connectorType: "notion" },
        ],
      },
      {
        id: "p2",
        name: "Pricing Copy Update",
        value: "Pending before launch",
        confidence: 0.7,
        freshness: "5 hr ago",
        sources: ["Notion Pricing Strategy"],
        sourceDocuments: [
          { id: "sd4", label: "Pricing strategy page", connectorType: "notion" },
        ],
      },
    ],
  },
  roadmap: {
    name: "Engineering Roadmap",
    description: "Delivery milestones, blockers, and active sequencing for core product work.",
    lastUpdated: "5 hr ago",
    components: [
      {
        id: "r1",
        name: "SSO Launch Target",
        value: "Q3",
        confidence: 0.92,
        freshness: "1 day ago",
        reviewStatus: "approved",
        reviewItemId: "rq3",
        reviewSummary: "The Q3 SSO target has already been approved.",
        sources: ["Notion Engineering Roadmap"],
        sourceDocuments: [
          { id: "sd3", label: "Engineering Roadmap", connectorType: "notion" },
        ],
      },
      {
        id: "r2",
        name: "SSO Rollout Blocker",
        value: "Audit review and enterprise procurement timing",
        confidence: 0.44,
        freshness: "5 hr ago",
        reviewStatus: "needs_review",
        reviewItemId: "rq2",
        reviewSummary: "The exact blocker still needs a human to confirm the canonical cause.",
        sources: ["Slack #product", "Notion Engineering Roadmap"],
        sourceDocuments: [
          { id: "sd2", label: "#product SSO blocker thread", connectorType: "slack" },
          { id: "sd3", label: "Engineering Roadmap", connectorType: "notion" },
        ],
      },
    ],
  },
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
        sourceDocuments: [
          { id: "sd5", label: "#finance revenue decision", connectorType: "slack" },
        ],
      },
      {
        id: "c2",
        name: "Net Revenue Retention",
        value: "112%",
        confidence: 0.88,
        freshness: "1 day ago",
        sources: ["Notion — Metrics DB"],
        sourceDocuments: [
          { id: "sd6", label: "Metrics DB", connectorType: "notion" },
        ],
      },
      {
        id: "c3",
        name: "Pipeline Coverage Ratio",
        value: "3.2x",
        confidence: 0.76,
        freshness: "3 days ago",
        sources: ["Gong transcripts", "Salesforce export"],
        reviewStatus: "needs_review",
        reviewItemId: "rq2",
        reviewSummary: "Pipeline coverage is still pending a human check against CRM hygiene updates.",
        sourceDocuments: [
          { id: "sd9", label: "Gong onboarding review", connectorType: "gong" },
        ],
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
        reviewStatus: "superseded",
        reviewItemId: "rq4",
        temporalState: "historical",
        reviewSummary: "This churn number is preserved for historical context and should not be treated as current truth.",
        sourceDocuments: [
          { id: "sd7", label: "CS tracker", connectorType: "notion" },
        ],
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
        sourceDocuments: [
          { id: "sd7", label: "CS tracker", connectorType: "notion" },
        ],
      },
      {
        id: "h2",
        name: "Avg. Weekly Active Users",
        value: "4,820",
        confidence: 0.95,
        freshness: "3 hr ago",
        sources: ["Analytics DB", "Slack #product"],
        sourceDocuments: [
          { id: "sd8", label: "#product usage update", connectorType: "slack" },
        ],
      },
      {
        id: "h3",
        name: "Support Ticket Volume",
        value: "38/week",
        confidence: 0.89,
        freshness: "6 hr ago",
        sources: ["Zendesk export"],
        sourceDocuments: [
          { id: "sd9", label: "Gong onboarding review", connectorType: "gong" },
        ],
      },
      {
        id: "h4",
        name: "Time to Value (Onboarding)",
        value: "4.2 days",
        confidence: 0.72,
        freshness: "5 days ago",
        sources: ["Gong transcripts", "Notion — Onboarding wiki"],
        reviewStatus: "needs_review",
        reviewItemId: "rq2",
        reviewSummary: "The onboarding metric is stale enough that the review queue should confirm the current baseline.",
        sourceDocuments: [
          { id: "sd7", label: "CS tracker", connectorType: "notion" },
          { id: "sd9", label: "Gong onboarding review", connectorType: "gong" },
        ],
      },
    ],
  },
};
