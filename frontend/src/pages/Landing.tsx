import { Link } from "react-router-dom";

const FEATURES = [
  { icon: "🩺", title: "Clinical Navigation", desc: "Agentic triage, red-flag escalation, clinician handoff and structured SOAP-ready case summaries." },
  { icon: "🧬", title: "Bioinformatics Workflows", desc: "Explore compound evidence, prepare reproducible network pharmacology and ADMET protocols, and design research before purchasing services." },
  { icon: "🌿", title: "Ethnobotanical Intelligence", desc: "Organize Nigerian medicinal-plant evidence, compounds, regional knowledge and discovery datasets." },
  { icon: "🔬", title: "Computational Drug Discovery", desc: "Build reproducible in-silico workflows for target mapping, docking, interaction networks and validation planning." },
  { icon: "📋", title: "Regulatory Workflows", desc: "Support evidence organization, compliance preparation and regulated product-development pathways." },
  { icon: "🌍", title: "Research Planning & Exports", desc: "Build downloadable project briefs and scientific reference records. Payments and full service fulfillment are later milestones." },
];

const WORKFLOWS = [
  ["Public Compound Explorer", "PubChem compound profiles and identifiers"],
  ["Protein Structure Lookup", "RCSB PDB experimental structure records"],
  ["Discovery Workbench", "Saved assets and screening job manifests"],
  ["Research Studio", "Polyherbal research project planning"],
  ["Reproducible Exports", "Research briefs and source-linked JSON"],
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-cream">
      <nav className="sticky top-0 z-50 flex items-center justify-between bg-forest-700 px-5 py-4 text-white shadow-md md:px-8">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">🌿</span>
          <div>
            <div className="text-lg font-bold text-gold-300">NigerFlora BioSciences</div>
            <div className="hidden text-xs text-forest-200 sm:block">Care · Research · Discovery</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/explore" className="rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600">Science Explorer</Link>
          <Link to="/bioinformatics-services" className="hidden rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600 sm:block">Services</Link>
          <Link to="/login" className="rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600">Sign In</Link>
          <Link to="/register" className="btn-secondary px-4 py-2 text-sm">Get Started</Link>
        </div>
      </nav>

      <section className="bg-hero-pattern text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-6 py-20 md:grid-cols-[1.2fr_0.8fr] md:py-28">
          <div>
            <div className="mb-5 inline-flex rounded-full bg-forest-800/70 px-4 py-2 text-sm font-medium text-gold-300">
              🇳🇬 Nigerian-built · 🌍 Global bioinformatics delivery
            </div>
            <h1 className="max-w-4xl text-4xl font-bold leading-tight md:text-6xl">
              From research question to <span className="text-gold-300">computational evidence</span>, tracked analysis and publication-ready outputs.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-forest-100">
              NigerFlora BioSciences combines responsible AI health workflows with bioinformatics workflows and guided research planning for M.Sc., Ph.D., research groups and academic departments.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link to="/explore" className="btn-secondary px-8 py-3 text-center text-base">Explore Real Compound Data →</Link>
              <Link to="/register" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Create Free Account</Link>
              <Link to="/research-studio" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Research Studio</Link>
            </div>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/10 p-6 backdrop-blur-sm">
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">Research functionality you can explore</div>
            <div className="mt-5 space-y-3">
              {WORKFLOWS.map(([name, detail]) => (
                <div key={name} className="flex items-center justify-between gap-3 rounded-xl bg-forest-900/35 px-4 py-3">
                  <span className="text-sm font-medium text-white">{name}</span>
                  <span className="max-w-[55%] text-right text-xs text-gold-300">{detail}</span>
                </div>
              ))}
            </div>
            <Link to="/explore" className="mt-5 block rounded-xl bg-gold-400 px-4 py-3 text-center text-sm font-bold text-forest-900">Open public science explorer</Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-18">
        <div className="py-16 text-center">
          <h2 className="text-3xl font-bold text-forest-800 md:text-4xl">One ecosystem for practical scientific research</h2>
          <p className="mx-auto mt-4 max-w-3xl text-gray-500">Built for researchers, clinicians, clinics, institutions, HMOs and responsible herbal-product innovators.</p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="card-hover">
              <div className="text-4xl">{feature.icon}</div>
              <h3 className="mt-4 text-xl font-bold text-forest-800">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-500">{feature.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-forest-800 px-6 py-16 text-white">
        <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
          {[
            ["1", "Explore", "Look up public compounds and protein structures with clear source references."],
            ["2", "Plan", "Choose your methodology and prepare a research brief before requesting any paid service."],
            ["3", "Export", "Download JSON references or Markdown study briefs for further analysis and review."],
          ].map(([step, title, text]) => (
            <div key={step} className="rounded-2xl border border-forest-600 p-6">
              <div className="text-2xl font-bold text-gold-300">{step}</div>
              <h3 className="mt-3 text-xl font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-forest-200">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="px-6 py-20 text-center">
        <h2 className="text-3xl font-bold text-forest-800 md:text-4xl">Begin with verifiable scientific information</h2>
        <p className="mx-auto mt-4 max-w-2xl text-gray-500">Search a public scientific database, export sourced results, and plan your next research step. Payments are separate from these tools.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link to="/explore" className="btn-primary inline-block px-10 py-3 text-base">Launch Science Explorer →</Link>
          <Link to="/register" className="btn-secondary inline-block px-10 py-3 text-base">Create Researcher Account</Link>
        </div>
      </section>

      <footer className="bg-forest-900 px-6 py-8 text-center text-sm text-forest-300">
        <div className="font-semibold text-gold-300">NigerFlora BioSciences</div>
        <p className="mt-2">© {new Date().getFullYear()} NigerFlora BioSciences · Powered by MABRIG Technologies</p>
        <p className="mt-2 text-xs text-forest-500">Clinical and in-silico outputs are decision-support and research evidence, not automatic proof of diagnosis, efficacy, safety or regulatory approval.</p>
      </footer>
    </div>
  );
}
