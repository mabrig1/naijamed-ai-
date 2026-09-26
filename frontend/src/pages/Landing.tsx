import { Link } from "react-router-dom";

const FEATURES = [
  { icon: "🩺", title: "Clinical Navigation", desc: "Agentic triage, red-flag escalation, clinician handoff and structured SOAP-ready case summaries." },
  { icon: "🧬", title: "Bioinformatics Consulting", desc: "Order network pharmacology, ADMET, molecular docking, Cytoscape networks and publication-ready figures with tracked delivery." },
  { icon: "🌿", title: "Ethnobotanical Intelligence", desc: "Organize Nigerian medicinal-plant evidence, compounds, regional knowledge and discovery datasets." },
  { icon: "🔬", title: "Computational Drug Discovery", desc: "Build reproducible in-silico workflows for target mapping, docking, interaction networks and validation planning." },
  { icon: "📋", title: "Regulatory Workflows", desc: "Support evidence organization, compliance preparation and regulated product-development pathways." },
  { icon: "🌍", title: "Local + Global Commerce", desc: "NGN and international service packages, secure checkout, project tracking and deliverable handoff." },
];

const REVENUE = [
  ["Scope Consultation", "₦25,000 / $39"],
  ["ADMET Screening", "From ₦75,000 / $110"],
  ["Network Pharmacology", "From ₦120,000 / $180"],
  ["Molecular Docking", "From ₦150,000 / $220"],
  ["M.Sc./Ph.D. Package", "From ₦300,000 / $450"],
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
          <Link to="/pricing" className="hidden rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600 sm:block">Plans & Pricing</Link>\n          <Link to="/bioinformatics-services" className="hidden rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600 md:block">Bioinformatics Services</Link>
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
              NigerFlora BioSciences combines responsible AI health workflows with paid bioinformatics consulting for M.Sc., Ph.D., research groups and academic departments.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link to="/pricing" className="btn-secondary px-8 py-3 text-center text-base">View Plans & Pricing →</Link>\n              <Link to="/bioinformatics-services" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Order Research Analysis</Link>
              <Link to="/register" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Create Free Account</Link>
              <Link to="/research-studio" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Research Studio</Link>
            </div>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/10 p-6 backdrop-blur-sm">
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">Orderable research services</div>
            <div className="mt-5 space-y-3">
              {REVENUE.map(([name, price]) => (
                <div key={name} className="flex items-center justify-between gap-3 rounded-xl bg-forest-900/35 px-4 py-3">
                  <span className="text-sm font-medium text-white">{name}</span>
                  <span className="text-sm font-bold text-gold-300">{price}</span>
                </div>
              ))}
            </div>
            <Link to="/bioinformatics-services" className="mt-5 block rounded-xl bg-gold-400 px-4 py-3 text-center text-sm font-bold text-forest-900">Get instant quote</Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-18">
        <div className="py-16 text-center">
          <h2 className="text-3xl font-bold text-forest-800 md:text-4xl">One ecosystem, multiple revenue and research pathways</h2>
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
            ["1", "Order", "Choose a defined bioinformatics package or request a custom project scope."],
            ["2", "Track", "Follow paid project status, target delivery, progress notes and receipts in your account."],
            ["3", "Deliver", "Receive reproducible methods, analysis tables, network files and publication-ready figures through secure links."],
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
        <h2 className="text-3xl font-bold text-forest-800 md:text-4xl">Need docking, ADMET or Cytoscape analysis this week?</h2>
        <p className="mx-auto mt-4 max-w-2xl text-gray-500">Start with a published package or send a custom scope. Local pricing is shown in Naira and international pricing in USD.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link to="/bioinformatics-services" className="btn-primary inline-block px-10 py-3 text-base">View Bioinformatics Services →</Link>
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
