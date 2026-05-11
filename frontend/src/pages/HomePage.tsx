import { Link } from "react-router-dom";

const FEATURES = [
  { icon: "🌱", title: "Herb Knowledge Base", desc: "Document and search Nigerian medicinal plants with AI-assisted botanical classification and phytochemical profiling." },
  { icon: "🤖", title: "AI Research Assistant", desc: "Powered by Google Gemini and Anthropic Claude to answer complex questions on herbal pharmacology." },
  { icon: "🏭", title: "Formulation Engine", desc: "AI-driven suggestions for pharmaceutical formulations derived from herbal extracts, with dosage and safety guidance." },
  { icon: "🗺️", title: "Supply Chain Tracker", desc: "End-to-end traceability from soil sample to finished product, ensuring quality and compliance." },
  { icon: "🔬", title: "Research Collaboration", desc: "Connect herbalists, researchers, and producers on a shared platform for knowledge exchange." },
  { icon: "📊", title: "Analytics & Reports", desc: "Data-driven insights into production trends, herb efficacy studies, and market demand signals." },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <section className="bg-gradient-to-br from-brand-800 to-brand-600 text-white py-24 px-4 text-center">
        <span className="text-6xl mb-4 block">🌿</span>
        <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
          From Soil to Science<br />to Pharmacy
        </h1>
        <p className="text-brand-100 text-lg max-w-2xl mx-auto mb-8">
          NigerFlora BioSciences connects centuries of Nigerian herbal wisdom with modern pharmaceutical
          production through the power of artificial intelligence.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link to="/register" className="bg-earth-500 hover:bg-earth-400 text-white font-medium text-base px-6 py-3 rounded-lg transition-colors">
            Start for Free
          </Link>
          <Link to="/herbs" className="border border-white text-white hover:bg-white/10 font-medium text-base px-6 py-3 rounded-lg transition-colors">
            Explore Herb Library
          </Link>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 py-20 grid md:grid-cols-3 gap-8">
        {FEATURES.map(({ icon, title, desc }) => (
          <div key={title} className="card hover:shadow-md transition-shadow">
            <span className="text-4xl mb-3 block">{icon}</span>
            <h3 className="font-semibold text-lg mb-2 text-brand-800">{title}</h3>
            <p className="text-gray-600 text-sm leading-relaxed">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
