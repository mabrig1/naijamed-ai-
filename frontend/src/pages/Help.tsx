import { useState } from "react";

interface Article { q: string; a: string; }
interface Section { title: string; icon: string; articles: Article[]; }

const SECTIONS: Section[] = [
  {
    title: "Getting Started",
    icon: "🚀",
    articles: [
      { q: "What is NigerFlora BioSciences?", a: "NigerFlora BioSciences is an AI-powered platform connecting Nigerian herbal farmers, researchers, and pharmaceutical companies — turning ancient herbal knowledge into validated, market-ready medicine." },
      { q: "How do I create an account?", a: "Click 'Get Started' on the home page, choose your role (Farmer, Researcher, or Pharma Company), fill in your name, email, and password, then click 'Create Account'. You'll be logged in immediately." },
      { q: "What are the user roles?", a: "Farmer: List herbs, track market demand, and connect with buyers. Researcher: Submit clinical trials, log patient outcomes, and access research tools. Pharma Company: Browse herbs, generate NAFDAC-ready formulations, and manage compliance docs. Admin: Full platform access including user management and analytics." },
      { q: "Is my data secure?", a: "Yes. All passwords are hashed with bcrypt, API calls use JWT authentication tokens, and all data is transmitted over HTTPS." },
    ],
  },
  {
    title: "For Farmers",
    icon: "🌱",
    articles: [
      { q: "How do I list my herbs for sale?", a: "Go to Farming → Create Listing. Fill in the herb name, quantity available (kg), price per kg, your region, and whether it's organic/NAFDAC certified. Your listing becomes immediately visible to buyers." },
      { q: "How do I track market demand?", a: "Go to Farming → Market Demand to see which herbs are most requested by pharma companies and researchers, along with price trends." },
      { q: "How do I export my herbs internationally?", a: "Go to Export Hub → Create Export Listing. This enters you into the export marketplace where global buyers can find and order your herbs. You can also get freight quotes and track shipments." },
    ],
  },
  {
    title: "For Researchers",
    icon: "🔬",
    articles: [
      { q: "How do I submit a clinical trial?", a: "Go to Research → Submit Trial. Provide the herb studied, trial phase, sample size, outcomes, and supporting documents. Admin review is required before public listing." },
      { q: "How do I log patient outcomes?", a: "Inside any clinical trial detail page, use the 'Log Outcome' button to record patient ID, treatment protocol, observed outcomes, and adverse effects." },
      { q: "How do I find evidence for a specific herb?", a: "Go to Research → Herb Evidence, select the herb from the dropdown, and view all associated trials, compounds, and published studies." },
    ],
  },
  {
    title: "For Pharma Companies",
    icon: "🏭",
    articles: [
      { q: "How do I generate a drug formulation?", a: "Go to Formulations → Create. Select the target herb, formulation type (capsule, tincture, etc.), dosage, and intended use. The AI assists with compound compatibility checks." },
      { q: "How do I generate NAFDAC documentation?", a: "Go to Compliance → New Document. Select NAFDAC as the document type, choose your formulation, and the AI will draft the required regulatory submission document." },
      { q: "How do I use the Compliance Chat assistant?", a: "Go to Compliance → AI Chat. Type your compliance question (NAFDAC, NEPC, SON requirements) and the AI will answer based on current Nigerian pharmaceutical regulations." },
    ],
  },
  {
    title: "Export & Logistics",
    icon: "🚢",
    articles: [
      { q: "How does the export marketplace work?", a: "Farmers create export listings with price, quantity, certifications, and delivery terms. Global buyers browse and place orders. Payments are held in escrow until delivery is confirmed." },
      { q: "How do I get a freight quote?", a: "Go to Logistics → Freight Calculator. Enter origin (your Nigerian location), destination country, and cargo weight/type. You'll get quotes from multiple freight carriers." },
      { q: "How does escrow work?", a: "When a buyer places an order, payment is held in escrow by NigerFlora. Once the shipment is delivered and confirmed, funds are released to the seller minus a 2.5% platform fee." },
      { q: "How do I track a shipment?", a: "Go to Logistics → Shipment Tracker and enter your shipment ID. You'll see real-time status updates from the carrier." },
    ],
  },
  {
    title: "AI Features",
    icon: "🤖",
    articles: [
      { q: "What can the AI Herb Assistant do?", a: "The AI Herb Assistant (powered by Google Gemini) can answer questions about any Nigerian herb — medicinal properties, traditional uses, known compounds, interactions, and cultivation advice." },
      { q: "What is the Customs AI Assistant?", a: "The Customs Assistant helps you understand Nigerian export/import requirements, HS codes for herbal products, NEPC certification requirements, and phytosanitary documentation." },
      { q: "How accurate is the Price Intelligence?", a: "Price Intelligence shows historical price trends for 15+ major Nigerian herbs across 3 regional markets. Data is updated monthly and sourced from market aggregators." },
    ],
  },
  {
    title: "Account & Security",
    icon: "🔐",
    articles: [
      { q: "I forgot my password. How do I reset it?", a: "Currently, contact the admin at admin@nigerflora.com with your registered email address to request a password reset." },
      { q: "How do I change my role?", a: "Role changes must be made by an admin. Contact admin@nigerflora.com with your request and reason." },
      { q: "How do I contact support?", a: "Email admin@nigerflora.com or use the admin contact form. Response time is typically within 24 hours." },
    ],
  },
];

const QUICK_STARTS = [
  { role: "Farmer", icon: "🌱", color: "bg-green-50 border-green-200", steps: ["Register as Farmer", "Create a Farm Listing", "Browse Export Marketplace", "Get Freight Quotes"] },
  { role: "Researcher", icon: "🔬", color: "bg-blue-50 border-blue-200", steps: ["Register as Researcher", "Browse Herb Database", "Submit a Clinical Trial", "Use Herb Evidence tool"] },
  { role: "Pharma Company", icon: "🏭", color: "bg-purple-50 border-purple-200", steps: ["Register as Pharma Company", "Browse Formulations", "Generate NAFDAC Docs", "Use Compliance Chat"] },
];

export default function Help() {
  const [search, setSearch] = useState("");
  const [openKey, setOpenKey] = useState<string | null>(null);

  const filtered = SECTIONS.map(s => ({
    ...s,
    articles: s.articles.filter(
      a => !search || a.q.toLowerCase().includes(search.toLowerCase()) || a.a.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter(s => s.articles.length > 0);

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-8 rounded-2xl">
        <h1 className="text-3xl font-bold mb-2">Help & Knowledge Base</h1>
        <p className="text-forest-100 mb-4">Everything you need to get the most out of NigerFlora BioSciences.</p>
        <input
          type="text"
          placeholder="Search help articles…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full rounded-xl px-4 py-3 text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-gold-400"
        />
      </div>

      {/* Quick Start */}
      {!search && (
        <div>
          <h2 className="text-xl font-bold text-forest-800 mb-4">Quick Start by Role</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {QUICK_STARTS.map(qs => (
              <div key={qs.role} className={`rounded-xl border p-4 ${qs.color}`}>
                <div className="text-2xl mb-2">{qs.icon}</div>
                <h3 className="font-bold text-gray-800 mb-3">{qs.role}</h3>
                <ol className="space-y-1">
                  {qs.steps.map((step, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="font-bold text-forest-600 shrink-0">{i + 1}.</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sections */}
      {filtered.length === 0 ? (
        <div className="text-center text-gray-500 py-12">No articles match your search.</div>
      ) : (
        filtered.map(section => (
          <div key={section.title}>
            <h2 className="text-lg font-bold text-forest-800 mb-3 flex items-center gap-2">
              <span>{section.icon}</span>{section.title}
            </h2>
            <div className="space-y-2">
              {section.articles.map(article => {
                const key = section.title + article.q;
                const open = openKey === key;
                return (
                  <div key={article.q} className="border border-gray-200 rounded-xl overflow-hidden">
                    <button
                      className="w-full text-left px-5 py-4 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors"
                      onClick={() => setOpenKey(open ? null : key)}
                    >
                      <span className="font-medium text-gray-800 text-sm">{article.q}</span>
                      <span className="text-gray-400 shrink-0 ml-2">{open ? "▲" : "▼"}</span>
                    </button>
                    {open && (
                      <div className="px-5 py-4 bg-gray-50 border-t border-gray-100 text-sm text-gray-700 leading-relaxed">
                        {article.a}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}

      {/* Contact */}
      <div className="bg-forest-50 border border-forest-200 rounded-2xl p-6 text-center">
        <div className="text-3xl mb-2">💬</div>
        <h3 className="font-bold text-forest-800 mb-1">Still need help?</h3>
        <p className="text-sm text-gray-600 mb-3">Our admin team responds within 24 hours.</p>
        <a
          href="mailto:admin@nigerflora.com"
          className="inline-block bg-forest-700 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-forest-800 transition-colors"
        >
          Email admin@nigerflora.com
        </a>
      </div>
    </div>
  );
}
