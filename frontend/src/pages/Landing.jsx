import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, History, ShieldAlert, Cpu, ArrowRight, BookOpen, AlertCircle, Database } from "lucide-react";

const PROBLEMS = [
  {
    icon: BookOpen,
    title: "Context drifts faster than docs updates",
    body: "In small startups, product truth changes in Slack, GitHub, and Notion long before a clean document catches up.",
  },
  {
    icon: Database,
    title: "Critical knowledge is siloed",
    body: "Founders, PMs, and lead engineers become the source of truth. Everyone else, including AI, works off partial context.",
  },
  {
    icon: AlertCircle,
    title: "Wrong context is expensive",
    body: "A stale roadmap, wrong pricing answer, or contradictory PR can create real customer and execution damage.",
  },
];

const CAPABILITIES = [
  {
    icon: CheckCircle2,
    title: "Remember Every Decision",
    body: "Keep track of exactly what changed in your startup, why it changed, and who made the call.",
  },
  {
    icon: History,
    title: "Rewind Your Startup's Brain",
    body: "Easily look up what your team agreed on last week or before your latest pivot.",
  },
  {
    icon: ShieldAlert,
    title: "Catch Mistakes Before Launch",
    body: "Automatically spot contradictions in your PRs or launch notes before customers see them.",
  },
  {
    icon: Cpu,
    title: "Answers You Can Trust",
    body: "Get answers with a direct link back to the exact Slack message or Notion page they came from.",
  },
];

const DIFFERENTIATORS = [
  "Built for fast-moving startups, not broad enterprise search.",
  "Optimized for quick pivots and volatile context.",
  "Focuses on what is true now, what used to be true, and why.",
  "Designed to ground AI agents with verified human truth.",
];

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(79,70,229,0.14),_transparent_32%),linear-gradient(180deg,#f8fafc_0%,#ffffff_42%,#eef2ff_100%)] text-slate-900 overflow-x-hidden">
      <header className="sticky top-0 z-50 border-b border-slate-200/50 bg-white/70 backdrop-blur-md supports-[backdrop-filter]:bg-white/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-600 shadow-[0_4px_20px_rgba(79,70,229,0.4)] text-sm font-semibold text-white">
              CE
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">Context Engine</p>
              <p className="text-xs text-slate-500">Source-backed startup memory</p>
            </div>
          </div>

          <nav className="hidden items-center gap-6 text-sm font-medium text-slate-500 md:flex">
            <a href="#problem" className="transition-colors hover:text-brand-600">Problem</a>
            <a href="#solution" className="transition-colors hover:text-brand-600">Solution</a>
            <a href="#fit" className="transition-colors hover:text-brand-600">Why startups</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/app"
              className="group relative flex items-center gap-2 overflow-hidden rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_0_15px_rgba(79,70,229,0.4)] transition-all duration-300 hover:bg-brand-500 hover:shadow-[0_0_30px_rgba(79,70,229,0.6)] hover:-translate-y-0.5"
            >
              <span className="relative z-10">Go to Dashboard</span>
              <ArrowRight className="relative z-10 h-4 w-4 transition-transform group-hover:translate-x-1" />
              <div className="absolute inset-0 z-0 bg-gradient-to-r from-brand-600 via-brand-400 to-brand-600 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="space-y-8"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-brand-700 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500"></span>
              </span>
              Built for high-velocity teams
            </div>

            <div className="space-y-5">
              <h1 className="max-w-3xl text-5xl font-bold tracking-tight text-slate-950 md:text-6xl md:leading-[1.05]">
                Your startup moves <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-400">faster</span> than its docs.
              </h1>
              <p className="max-w-2xl text-lg leading-relaxed text-slate-600">
                Context Engine turns Slack, Notion, GitHub, and other internal sources into a
                source-backed memory of what your company believes, what changed, and why.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <Link
                to="/app"
                className="group flex items-center gap-2 rounded-2xl bg-slate-950 px-6 py-3.5 text-sm font-semibold text-white shadow-xl shadow-slate-950/20 transition-all duration-300 hover:-translate-y-1 hover:bg-slate-900 hover:shadow-2xl hover:shadow-slate-950/30"
              >
                Try Context Engine
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <a
                href="#solution"
                className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur-sm px-6 py-3.5 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-300 hover:bg-slate-50 hover:shadow-md hover:-translate-y-1"
              >
                See how it works
              </a>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Metric label="Never Forget" value="Source-backed" />
              <Metric label="Rewind Time" value="Query old truth" />
              <Metric label="Catch Mistakes" value="Stop contradictions" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="rounded-[32px] border border-white/40 bg-white/60 p-2 shadow-[0_32px_80px_-24px_rgba(79,70,229,0.2)] backdrop-blur-xl"
          >
            <div className="rounded-[24px] border border-slate-100 bg-white p-6 shadow-inner">
              <div className="flex items-center justify-between mb-6">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
                  Example workflow
                </p>
                <div className="flex gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-red-400"></div>
                  <div className="h-2 w-2 rounded-full bg-yellow-400"></div>
                  <div className="h-2 w-2 rounded-full bg-green-400"></div>
                </div>
              </div>
              <div className="space-y-4">
                <FlowRow
                  icon={<History className="h-4 w-4 text-brand-500" />}
                  title="Ingest"
                  body="Slack, Notion, GitHub, and other tools sync securely."
                />
                <FlowRow
                  icon={<Cpu className="h-4 w-4 text-brand-500" />}
                  title="Resolve truth"
                  body="Extracts facts, conflicts, and superseded decisions."
                />
                <FlowRow
                  icon={<CheckCircle2 className="h-4 w-4 text-brand-500" />}
                  title="Answer safely"
                  body="Agents get grounded answers with confidence & provenance."
                />
                <FlowRow
                  icon={<ShieldAlert className="h-4 w-4 text-brand-500" />}
                  title="Push context back"
                  body="Check PRs and customer chats against current truth."
                />
              </div>
            </div>
          </motion.div>
        </section>

        {/* LOGOS SECTION */}
        <section className="border-y border-slate-200/50 bg-white/40 py-10 backdrop-blur-sm">
          <div className="mx-auto max-w-6xl px-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-6">Works smoothly with your favorite tools</p>
            <div className="flex flex-wrap items-center justify-center gap-8 opacity-60 transition-opacity hover:opacity-100 md:gap-14">
              <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-800">
                <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="h-7 w-7"><title>Slack</title><path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.27 0a2.527 2.527 0 0 1 2.521-2.52 2.528 2.528 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.27a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.523a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.835zm-1.27 0a2.528 2.528 0 0 1-2.521 2.521 2.528 2.528 0 0 1-2.521-2.521V2.522A2.528 2.528 0 0 1 15.166 0a2.528 2.528 0 0 1 2.52 2.522v6.313zM15.166 18.958a2.528 2.528 0 0 1 2.52 2.522A2.528 2.528 0 0 1 15.166 24a2.528 2.528 0 0 1-2.521-2.522v-2.52h2.521zm0-1.27a2.528 2.528 0 0 1-2.52-2.521 2.528 2.528 0 0 1 2.52-2.521h6.313A2.528 2.528 0 0 1 24 15.166a2.528 2.528 0 0 1-2.522 2.52h-6.313z"/></svg>
                Slack
              </div>
              <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-800">
                <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="h-7 w-7"><title>Notion</title><path d="M4.1 3.511a1.27 1.27 0 0 1 1.282-1.2h12.5a1.27 1.27 0 0 1 1.283 1.2l.006 17a1.27 1.27 0 0 1-1.281 1.21h-12.5a1.28 1.28 0 0 1-1.283-1.196zm2.4 2.87v10.15l7.98-10.15h1.99V17h-1.84V7.53L7.33 17.02H5.34v-10.64h1.16z" /></svg>
                Notion
              </div>
              <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-800">
                <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="h-7 w-7"><title>GitHub</title><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                GitHub
              </div>
              <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-800">
                <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="h-7 w-7"><title>Jira</title><path d="M11.53 17.53A4.53 4.53 0 0 1 7 13V2.47a.47.47 0 0 0-.47-.47H2.47A.47.47 0 0 0 2 2.47V13a9.06 9.06 0 0 0 9.06 9.06h8.47a.47.47 0 0 0 .47-.47v-4.06a.47.47 0 0 0-.47-.47h-8.06zM21.53 9.47A9.06 9.06 0 0 0 12.47.41h-2A.47.47 0 0 0 10 .88v4.06A.47.47 0 0 0 10.47 5.4h2A4.53 4.53 0 0 1 17 9.94v8.06a.47.47 0 0 0 .47.47h4.06a.47.47 0 0 0 .47-.47V9.47z"/></svg>
                Jira
              </div>
              <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-800">
                <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 -ml-1"><title>Zoom</title><path d="M4.5 9A2.5 2.5 0 0 0 2 11.5v4A2.5 2.5 0 0 0 4.5 18h8A2.5 2.5 0 0 0 15 15.5v-4A2.5 2.5 0 0 0 12.5 9h-8zm11.2 5.5v-4a1 1 0 0 1 1.5-.86l4 2.5a1 1 0 0 1 0 1.72l-4 2.5a1 1 0 0 1-1.5-.86z"/></svg>
                Zoom
              </div>
            </div>
          </div>
        </section>

        <section id="problem" className="bg-white/70 backdrop-blur-md">
          <div className="mx-auto max-w-6xl px-6 py-24">
            <motion.div
              initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
              variants={itemVariants}
              className="max-w-3xl"
            >
              <p className="text-lg font-bold uppercase tracking-widest text-brand-600">The Startup Problem</p>
              <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-950 md:text-5xl">
                Search is not the hard part. <span className="text-slate-400">Keeping company truth aligned is.</span>
              </h2>
            </motion.div>

            <motion.div
              initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }}
              variants={containerVariants}
              className="mt-12 grid gap-6 md:grid-cols-3"
            >
              {PROBLEMS.map((item) => (
                <motion.div
                  variants={itemVariants}
                  key={item.title}
                  className="group rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:border-brand-300 hover:shadow-xl hover:shadow-brand-500/10"
                >
                  <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 transition-colors group-hover:bg-brand-600 group-hover:text-white">
                    <item.icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">{item.title}</h3>
                  <p className="mt-3 text-base leading-relaxed text-slate-600">{item.body}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        <section id="solution" className="mx-auto max-w-6xl px-6 py-24">
          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
            variants={itemVariants}
            className="max-w-3xl"
          >
            <p className="text-lg font-bold uppercase tracking-widest text-brand-600">What Context Engine Does</p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-950 md:text-5xl">
              Gives your team a <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-400">grounded memory.</span>
            </h2>
          </motion.div>

          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }}
            variants={containerVariants}
            className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4"
          >
            {CAPABILITIES.map((item) => (
              <motion.div
                variants={itemVariants}
                key={item.title}
                className="group rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:border-brand-300 hover:shadow-xl hover:shadow-brand-500/10"
              >
                <div className="mb-5 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50 text-slate-600 transition-colors group-hover:bg-brand-50 group-hover:text-brand-600">
                  <item.icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">{item.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-600">{item.body}</p>
              </motion.div>
            ))}
          </motion.div>
        </section>

        <section id="fit" className="relative overflow-hidden bg-slate-950 text-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(79,70,229,0.15),_transparent_40%)]" />

          <div className="relative mx-auto grid max-w-6xl gap-16 px-6 py-24 lg:grid-cols-[1fr_1.1fr] lg:items-center">
            <motion.div
              initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
              variants={itemVariants}
            >
              <p className="text-lg font-bold uppercase tracking-widest text-brand-400">Why Startups Choose This</p>
              <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-5xl">
                Corporate tools optimize for breadth. <br /><span className="text-slate-400">You need truth under velocity.</span>
              </h2>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
                Small teams have fewer employees, but far more context density per person. Decisions
                move quickly, documentation lags, and a single contradiction can damage a launch,
                customer call, or roadmap commitment.
              </p>
            </motion.div>

            <motion.div
              initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }}
              variants={containerVariants}
              className="space-y-4"
            >
              {DIFFERENTIATORS.map((item, i) => (
                <motion.div
                  variants={itemVariants}
                  key={i}
                  className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 px-6 py-5 transition-colors hover:bg-white/10 hover:border-brand-500/50"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 group-hover:bg-brand-500 group-hover:text-white transition-colors duration-300">
                    <CheckCircle2 className="h-5 w-5" />
                  </div>
                  <p className="text-base font-medium leading-relaxed text-slate-200">{item}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-24">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
            className="relative overflow-hidden rounded-[40px] border border-brand-200 bg-white p-10 shadow-2xl shadow-brand-500/10 md:p-16"
          >
            <div className="absolute top-0 right-0 -mr-20 -mt-20 h-64 w-64 rounded-full bg-brand-500/10 blur-3xl mix-blend-multiply" />
            <div className="absolute bottom-0 left-0 -ml-20 -mb-20 h-64 w-64 rounded-full bg-brand-400/10 blur-3xl mix-blend-multiply" />

            <div className="relative max-w-3xl space-y-6">
              <p className="text-lg font-bold uppercase tracking-widest text-brand-600">The Pitch</p>
              <h2 className="text-4xl font-bold tracking-tight text-slate-950 md:text-5xl">
                Search finds documents. <br />Context Engine tells your team <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-400">what is actually true.</span>
              </h2>
              <p className="text-lg leading-relaxed text-slate-600 md:text-xl">
                Use it to answer questions with provenance, understand how decisions evolved, and stop
                stale or contradictory context from slipping into product, engineering, or customer work.
              </p>
            </div>

            <div className="relative mt-10 flex flex-wrap gap-4">
              <Link
                to="/app"
                className="group flex items-center gap-2 rounded-2xl bg-brand-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-brand-500/30 transition-all duration-300 hover:-translate-y-1 hover:bg-brand-500 hover:shadow-xl hover:shadow-brand-500/40"
              >
                Try Context Engine
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </motion.div>
        </section>
      </main>

      <footer className="border-t border-slate-200/50 bg-white/80 py-12 text-center text-sm font-medium text-slate-500 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 md:flex-row">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-xs font-bold text-white">CE</span>
            <p>© {new Date().getFullYear()} Context Engine. All rights reserved.</p>
          </div>
          <div className="flex gap-8">
            <a href="#" className="transition-colors hover:text-brand-600">Documentation</a>
            <a href="#" className="transition-colors hover:text-brand-600">Pricing</a>
            <a href="#" className="transition-colors hover:text-brand-600">Privacy & Security</a>
            <a href="#" className="transition-colors hover:text-brand-600">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-brand-100 bg-white/60 px-5 py-4 shadow-[0_4px_20px_-4px_rgba(79,70,229,0.05)] backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-[0_8px_30px_-4px_rgba(79,70,229,0.1)]">
      <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-600">{label}</p>
      <p className="mt-2 text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}

function FlowRow({ icon, title, body }) {
  return (
    <div className="group flex gap-4 rounded-xl border border-slate-100 bg-slate-50/50 p-4 transition-all duration-300 hover:bg-brand-50 hover:border-brand-200 hover:shadow-md hover:shadow-brand-500/5">
      <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white shadow-sm transition-transform duration-300 group-hover:scale-110">
        {icon}
      </div>
      <div>
        <p className="text-sm font-bold text-slate-900 transition-colors group-hover:text-brand-700">{title}</p>
        <p className="mt-1 text-sm leading-relaxed text-slate-600">{body}</p>
      </div>
    </div>
  );
}
