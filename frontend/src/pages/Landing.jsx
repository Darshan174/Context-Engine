import { Link } from "react-router-dom";

const PROBLEMS = [
  {
    title: "Context drifts faster than docs update",
    body: "In small startups, product truth changes in Slack, GitHub, and Notion long before a clean document catches up.",
  },
  {
    title: "A few people carry too much of the company in their heads",
    body: "Founders, PMs, and lead engineers become the source of truth. Everyone else, including AI, works off partial context.",
  },
  {
    title: "Wrong context is expensive",
    body: "A stale roadmap, wrong pricing answer, or contradictory PR can create real customer and execution damage.",
  },
];

const CAPABILITIES = [
  {
    title: "Decision Memory",
    body: "Track what changed, why it changed, and which source approved it.",
  },
  {
    title: "Time-Travel Context",
    body: "Ask what the company believed last week, last month, or before a pivot.",
  },
  {
    title: "Source-Backed Answers",
    body: "Every answer comes with a traceable audit trail to the exact Slack message, Notion page, or source document.",
  },
  {
    title: "Launch Guard",
    body: "Catch contradictions before they reach a PR, launch note, sales response, or customer conversation.",
  },
];

const DIFFERENTIATORS = [
  "Built for fast-moving teams of 5-15, not broad enterprise search.",
  "Optimized for context volatility, not connector count.",
  "Focuses on what is true now, what used to be true, and why it changed.",
  "Designed to support both humans and AI agents with the same grounded context.",
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(79,70,229,0.14),_transparent_32%),linear-gradient(180deg,#f8fafc_0%,#ffffff_42%,#eef2ff_100%)] text-slate-900">
      <header className="border-b border-slate-200/70 bg-white/70 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-600 text-sm font-semibold text-white shadow-sm">
              CE
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">Context Engine</p>
              <p className="text-xs text-slate-500">Source-backed startup memory</p>
            </div>
          </div>

          <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#problem" className="transition-colors hover:text-slate-900">
              Problem
            </a>
            <a href="#solution" className="transition-colors hover:text-slate-900">
              Solution
            </a>
            <a href="#fit" className="transition-colors hover:text-slate-900">
              Why startups
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/app"
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Open Admin
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl gap-12 px-6 py-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
              Built for small startup teams
            </div>

            <div className="space-y-5">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl md:leading-[1.05]">
                Your startup moves faster than its docs.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg">
                Context Engine turns Slack, Notion, GitHub, and other internal sources into a
                source-backed memory of what your company believes, what changed, and why.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/app"
                className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-slate-900"
              >
                Explore the product
              </Link>
              <a
                href="#solution"
                className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              >
                See how it works
              </a>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="Decision memory" value="Always source-backed" />
              <Metric label="Time-travel context" value="Query old truth" />
              <Metric label="Pre-flight review" value="Catch contradictions" />
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-[0_24px_80px_-36px_rgba(15,23,42,0.28)]">
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                Example workflow
              </p>
              <div className="mt-5 space-y-4">
                <FlowRow
                  title="Ingest"
                  body="Slack, Notion, GitHub, and other tools sync into source documents."
                />
                <FlowRow
                  title="Resolve truth"
                  body="The engine extracts facts, relationships, conflicts, and superseded decisions."
                />
                <FlowRow
                  title="Answer safely"
                  body="Humans and AI agents get grounded answers with confidence, freshness, and provenance."
                />
                <FlowRow
                  title="Push context back"
                  body="PRs, launch notes, and customer-facing work can be checked against current truth."
                />
              </div>
            </div>
          </div>
        </section>

        <section id="problem" className="border-y border-slate-200/70 bg-white/70">
          <div className="mx-auto max-w-6xl px-6 py-18">
            <div className="max-w-3xl">
              <p className="text-sm font-medium text-brand-700">The startup problem</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
                Search is not the hard part. Keeping company truth aligned is.
              </h2>
            </div>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {PROBLEMS.map((item) => (
                <div
                  key={item.title}
                  className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="solution" className="mx-auto max-w-6xl px-6 py-18">
          <div className="max-w-3xl">
            <p className="text-sm font-medium text-brand-700">What Context Engine does</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              It gives your team and your agents a grounded operating memory.
            </h2>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {CAPABILITIES.map((item) => (
              <div
                key={item.title}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="fit" className="bg-slate-950 text-white">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-18 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div>
              <p className="text-sm font-medium text-brand-200">Why small startups choose this</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
                Bigger company tools optimize for breadth. You need truth under volatility.
              </h2>
              <p className="mt-5 max-w-xl text-sm leading-7 text-slate-300">
                Small teams have fewer employees, but far more context density per person. Decisions
                move quickly, documentation lags, and a single contradiction can damage a launch,
                customer call, or roadmap commitment.
              </p>
            </div>

            <div className="space-y-3">
              {DIFFERENTIATORS.map((item) => (
                <div
                  key={item}
                  className="flex gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-4"
                >
                  <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-brand-300" />
                  <p className="text-sm leading-6 text-slate-200">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-18">
          <div className="rounded-[32px] border border-slate-200 bg-white p-8 shadow-sm md:p-12">
            <div className="max-w-3xl space-y-4">
              <p className="text-sm font-medium text-brand-700">The pitch</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
                Search finds documents. Context Engine tells your team what is actually true.
              </h2>
              <p className="text-sm leading-7 text-slate-600 md:text-base">
                Use it to answer questions with provenance, understand how decisions evolved, and stop
                stale or contradictory context from slipping into product, engineering, or customer work.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/app"
                className="rounded-2xl bg-brand-600 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-brand-700"
              >
                Open the product
              </Link>
              <a
                href="#problem"
                className="rounded-2xl border border-slate-200 px-5 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              >
                Review the problem
              </a>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-4 shadow-sm">
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function FlowRow({ title, body }) {
  return (
    <div className="rounded-2xl border border-white/80 bg-white p-4 shadow-sm">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}
