import { Link } from "react-router-dom";

const FEATURES = [
  { icon: "🩺", title: "Clinical Navigation", desc: "Agentic triage, red-flag escalation, clinician handoff and structured SOAP-ready case summaries." },
  { icon: "🧬", title: "Research & Discovery Studio", desc: "Paid network pharmacology, ADMET, molecular docking, scientific figures, grant architecture and training." },
  { icon: "🌿", title: "Ethnobotanical Intelligence", desc: "Organize Nigerian medicinal-plant evidence, compounds, regional knowledge and discovery datasets." },
  { icon: "🔬", title: "Computational Drug Discovery", desc: "Build reproducible in-silico workflows for target mapping, docking, interaction networks and validation planning." },
  { icon: "📋", title: "Regulatory Workflows", desc: "Support evidence organization, compliance preparation and regulated product-development pathways." },
  { icon: "🌍", title: "Commercialization Tools", desc: "Connect research, providers, payments, export workflows and product-development services in one ecosystem." },
];

const REVENUE = [
  ["Network Pharmacology", "From ₦120,000"],
  ["ADMET Screening", "From ₦75,000"],
  ["Molecular Docking", "From ₦150,000"],
  ["In-Silico Thesis Package", "From ₦280,000"],
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
          <Link to="/login" className="rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-600">Sign In</Link>
          <Link to="/register" className="btn-secondary px-4 py-2 text-sm">Get Started</Link>
        </div>
      </nav>

      <section className="bg-hero-pattern text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-6 py-20 md:grid-cols-[1.2fr_0.8fr] md:py-28">
          <div>
            <div className="mb-5 inline-flex rounded-full bg-forest-800/70 px-4 py-2 text-sm font-medium text-gold-300">
              🇳🇬 Nigerian-built bioscience and healthcare intelligence
            </div>
            <h1 className="max-w-4xl text-4xl font-bold leading-tight md:text-6xl">
              From ethnobotanical knowledge to <span className="text-gold-300">computational evidence</span>, clinical coordination and regulated innovation.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-forest-100">
              NigerFlora BioSciences combines responsible AI health workflows, bioinformatics consulting, polyherbal research, postgraduate services and commercialization infrastructure in one Vercel-native platform.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/register" className="btn-secondary px-8 py-3 text-center text-base">Create Free Account →</Link>
              <Link to="/research-studio" className="btn-outline border-white px-8 py-3 text-center text-base text-white hover:bg-white/10">Explore Research Studio</Link>
            </div>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/10 p-6 backdrop-blur-sm">
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">High-value research services</div>
            <div className="mt-5 space-y-3">
              {REVENUE.map(([name, price]) => (
                <div key={name} className="flex items-center justify-between gap-3 rounded-xl bg-forest-900/35 px-4 py-3">
                  <span className="text-sm font-medium text-white">{name}</span>
                  <span className="text-sm font-bold text-gold-300">{price}</span>
                </div>
              ))}
            </div>
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
            ["1", "Research", "Generate reproducible computational evidence and structured research outputs."],
            ["2", "Validate", "Move promising findings into appropriate experimental, clinical and professional review."],
            ["3", "Commercialize", "Build grant, IP, regulatory and market pathways without overstating computational predictions."],
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
        <h2 className="text-3xl font-bold text-forest-800 md:text-4xl">Build, publish, validate and monetize responsibly.</h2>
        <p className="mx-auto mt-4 max-w-2xl text-gray-500">Start with a researcher account for computational services, or choose the health/provider workspace that fits your role.</p>
        <Link to="/register" className="btn-primary mt-8 inline-block px-10 py-3 text-base">Start on NigerFlora →</Link>
      </section>

      <footer className="bg-forest-900 px-6 py-8 text-center text-sm text-forest-300">
        <div className="font-semibold text-gold-300">NigerFlora BioSciences</div>
        <p className="mt-2">© {new Date().getFullYear()} NigerFlora BioSciences · Powered by MABRIG Technologies</p>
        <p className="mt-2 text-xs text-forest-500">Clinical and in-silico outputs are decision-support and research evidence, not automatic proof of diagnosis, efficacy, safety or regulatory approval.</p>
      </footer>
    </div>
  );
}
