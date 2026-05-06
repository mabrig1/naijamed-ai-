import { Link } from "react-router-dom";

const FEATURES = [
  { icon: "🌿", title: "Herb Database", desc: "Browse 20+ Nigerian medicinal herbs with multilingual names, compounds, and regional data." },
  { icon: "🔬", title: "AI Formulation Lab", desc: "Generate pharmaceutical drug formulations powered by Claude AI — from tablet to syrup to extract." },
  { icon: "🌾", title: "Farm Marketplace", desc: "Farmers list harvests. Pharma companies browse, filter, and inquire with one click." },
  { icon: "📊", title: "Research Hub", desc: "Submit clinical trials, log anonymized patient outcomes, and get AI evidence scores." },
  { icon: "📋", title: "NAFDAC Compliance", desc: "Auto-fill regulatory documents, track approval stages, and chat with an AI compliance expert." },
  { icon: "📈", title: "Market Intelligence", desc: "AI demand forecasts, price trends, and planting recommendations tailored to Nigerian seasons." },
];

const STEPS = [
  { n: "01", title: "Register & Pick Your Role", desc: "Farmer, Researcher, Pharma Company — your role unlocks a tailored dashboard." },
  { n: "02", title: "Connect with the Ecosystem", desc: "Farmers list herbs. Researchers submit trials. Pharma companies buy and formulate." },
  { n: "03", title: "Let AI Accelerate Science", desc: "Claude and Gemini analyse herbs, generate formulations, and navigate NAFDAC regulations." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-cream">
      {/* Navbar */}
      <nav className="bg-forest-600 text-white px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-md">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">🌿</span>
          <div>
            <div className="font-bold text-lg text-gold-300">NaijaMed AI</div>
            <div className="text-xs text-forest-200 hidden sm:block">From Soil to Science to Pharmacy</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-forest-100 hover:text-white text-sm font-medium px-3 py-1.5 rounded-md hover:bg-forest-500 transition-colors">
            Sign In
          </Link>
          <Link to="/register" className="btn-secondary text-sm px-4 py-2">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-hero-pattern text-white">
        <div className="max-w-6xl mx-auto px-6 py-20 md:py-32 flex flex-col md:flex-row items-center gap-12">
          <div className="flex-1 text-center md:text-left">
            <div className="inline-flex items-center gap-2 bg-forest-700/60 text-gold-300 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
              🇳🇬 Proudly Nigerian · AI-Powered
            </div>
            <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
              From{" "}
              <span className="text-gold-300">Soil</span>
              {" "}to{" "}
              <span className="text-gold-300">Science</span>
              {" "}to{" "}
              <span className="text-gold-300">Pharmacy</span>
            </h1>
            <p className="text-forest-100 text-lg md:text-xl leading-relaxed mb-8 max-w-xl">
              The all-in-one AI platform connecting Nigerian herbal farmers, researchers, and pharmaceutical companies — turning ancient knowledge into modern medicine.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center md:justify-start">
              <Link to="/register" className="btn-secondary text-base px-8 py-3">
                Start Your Journey →
              </Link>
              <Link to="/login" className="btn-outline border-white text-white hover:bg-white/10 text-base px-8 py-3">
                Sign In
              </Link>
            </div>
          </div>
          <div className="flex-shrink-0 text-center">
            <div className="w-64 h-64 md:w-80 md:h-80 bg-forest-500/30 rounded-full flex items-center justify-center border-4 border-gold-400/40">
              <div className="text-9xl md:text-[120px] leading-none">🌿</div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="bg-gold-400 text-forest-900">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          {[
            ["20+", "Nigerian Herbs"],
            ["8", "NAFDAC Stages"],
            ["2 AI Models", "Claude + Gemini"],
            ["5 Roles", "Full Ecosystem"],
          ].map(([val, label]) => (
            <div key={label}>
              <div className="font-bold text-2xl md:text-3xl">{val}</div>
              <div className="text-forest-700 text-sm font-medium">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-forest-700 mb-4">
            Everything the Industry Needs
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto">
            One platform. Six powerful modules. Built for every stakeholder in the Nigerian herbal medicine value chain.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="card-hover group">
              <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">{f.icon}</div>
              <h3 className="text-lg font-bold text-forest-700 mb-2">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-forest-600 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gold-300 mb-3">How It Works</h2>
            <p className="text-forest-200">Simple. Powerful. Nigerian-built.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {STEPS.map((s) => (
              <div key={s.n} className="text-center">
                <div className="w-16 h-16 bg-gold-400 text-forest-900 rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                  {s.n}
                </div>
                <h3 className="font-bold text-lg mb-2">{s.title}</h3>
                <p className="text-forest-200 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 text-center px-6">
        <h2 className="text-3xl md:text-4xl font-bold text-forest-700 mb-4">
          Ready to Transform Nigerian Herbal Medicine?
        </h2>
        <p className="text-gray-500 mb-8 max-w-xl mx-auto">
          Join farmers, researchers, and pharma companies already using NaijaMed AI to accelerate drug discovery.
        </p>
        <Link to="/register" className="btn-primary text-base px-10 py-3">
          Create Free Account →
        </Link>
      </section>

      {/* Footer */}
      <footer className="bg-forest-800 text-forest-300 py-8 text-center text-sm">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-xl">🌿</span>
          <span className="text-gold-300 font-semibold">NaijaMed AI</span>
        </div>
        <p>© {new Date().getFullYear()} NaijaMed AI · Empowering Nigerian Herbal Medicine</p>
        <p className="text-forest-500 text-xs mt-2">AI guidance is informational only — always consult a certified NAFDAC regulatory consultant.</p>
      </footer>
    </div>
  );
}
