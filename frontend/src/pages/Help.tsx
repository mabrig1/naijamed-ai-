import { useState, useMemo } from "react";
import { Link } from "react-router-dom";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FAQ {
  q: string;
  a: string;
}

interface Section {
  id: string;
  icon: string;
  title: string;
  faqs: FAQ[];
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const QUICK_START_CARDS = [
  {
    icon: "🌾",
    role: "Farmer",
    desc: "List your herbal harvests, track buyer demand, and access planting recommendations.",
    steps: [
      "Register with the Farmer role",
      "Create a farm listing",
      "Monitor inquiries from pharma buyers",
    ],
    link: "/register",
  },
  {
    icon: "🔬",
    role: "Researcher",
    desc: "Submit clinical trials, upload patient outcome data, and access AI evidence scoring.",
    steps: [
      "Register with the Researcher role",
      "Submit a clinical trial record",
      "Review AI-generated evidence scores",
    ],
    link: "/register",
  },
  {
    icon: "🏭",
    role: "Pharma Company",
    desc: "Source herbs directly, generate NAFDAC-ready formulations, and track compliance stages.",
    steps: [
      "Register with the Pharma Company role",
      "Browse the farm marketplace",
      "Run the AI Formulation Lab",
    ],
    link: "/register",
  },
  {
    icon: "🚢",
    role: "Exporter / Logistics",
    desc: "Create export listings, get AI-generated freight quotes, and manage escrow payments.",
    steps: [
      "Register with the Exporter role",
      "Create an export listing",
      "Receive and confirm freight quotes",
    ],
    link: "/register",
  },
  {
    icon: "🛡️",
    role: "Admin",
    desc: "Manage users, verify listings, oversee platform compliance and system settings.",
    steps: [
      "Access the admin panel from your dashboard",
      "Review pending verifications",
      "Manage user roles and permissions",
    ],
    link: "/login",
  },
];

const SECTIONS: Section[] = [
  {
    id: "getting-started",
    icon: "🚀",
    title: "Getting Started",
    faqs: [
      {
        q: "What is NigerFlora BioSciences (NaijaMed AI)?",
        a: "NigerFlora BioSciences, also known as NaijaMed AI, is an AI-powered platform that digitises Nigeria's herbal medicine value chain. It connects farmers who grow medicinal herbs with researchers conducting clinical studies, pharmaceutical companies formulating medicines, and exporters moving products to global markets — all validated and streamlined by Claude and Gemini AI models.",
      },
      {
        q: "How do I create an account?",
        a: "Click 'Get Started' or 'Register' on the landing page. Fill in your full name, email address, and a secure password. Most importantly, select your role (Farmer, Researcher, Pharma Company, Exporter, or Admin). Your role determines which dashboard modules and features are unlocked for you. After submitting, you will receive a confirmation and can sign in immediately.",
      },
      {
        q: "What roles are available on the platform?",
        a: "There are five roles: (1) Farmer — list herbs, track demand, access planting tips; (2) Researcher — submit clinical trials and patient outcomes; (3) Pharma Company — source herbs, generate formulations, manage NAFDAC compliance; (4) Exporter / Logistics — manage export listings, freight quotes, and escrow; (5) Admin — oversee the entire platform, verify users, and manage settings. Each role has a tailored dashboard.",
      },
      {
        q: "Can I change my role after registering?",
        a: "Role changes must be requested through your account settings or by contacting the platform administrator. Because each role grants access to distinct data and features, role switches are reviewed to prevent misuse. In many cases you may hold a secondary role if your business operates across multiple areas — contact support to discuss your situation.",
      },
      {
        q: "Is the platform free to use?",
        a: "Core features — herb browsing, farm listings, research submissions, and AI assistance — are available on the free tier. Advanced features such as bulk export management, NAFDAC document generation, and priority AI processing may require a paid subscription. Check the Pricing page or contact sales for current plan details.",
      },
      {
        q: "Which AI models power the platform?",
        a: "NaijaMed AI uses Anthropic's Claude for formulation lab, compliance guidance, and contextual Q&A, and Google Gemini for herb database enrichment and market intelligence. Both models are prompted with Nigerian pharmaceutical context and NAFDAC regulatory knowledge to deliver locally relevant outputs.",
      },
    ],
  },
  {
    id: "farmers",
    icon: "🌾",
    title: "For Farmers",
    faqs: [
      {
        q: "How do I create a farm listing?",
        a: "From your Farmer dashboard, navigate to 'My Farm Listings' and click 'New Listing'. Fill in the herb name (common, Yoruba, Igbo, Hausa, and Latin names if known), quantity available, harvest date, price per kg, GPS location (optional), and any certifications. Publish the listing — it will immediately be visible to pharma companies and exporters browsing the marketplace.",
      },
      {
        q: "How do I know which herbs are in demand?",
        a: "Your dashboard includes a 'Demand Tracker' panel powered by AI market intelligence. It shows demand trends for each listed herb over the past 30 and 90 days, highlights which herbs are experiencing price surges, and provides seasonal planting recommendations so you can plan ahead. You will also receive notifications when a pharma company inquires about an herb you grow.",
      },
      {
        q: "Can I update my listing after publishing?",
        a: "Yes. Open the listing from 'My Farm Listings', click 'Edit', change any field (quantity, price, availability date), and save. Updates are reflected immediately. If your stock runs out, mark the listing as 'Sold Out' rather than deleting it — this preserves your inquiry history and lets buyers request a back-order.",
      },
      {
        q: "How do buyers contact me?",
        a: "When a pharma company or exporter is interested, they send an inquiry through the platform. You will receive an in-app notification and an optional email alert. All communication stays within the platform messaging system to maintain a verifiable record. You can accept, counter-offer, or decline any inquiry.",
      },
      {
        q: "What are the AI planting recommendations?",
        a: "The AI analyses historical Nigerian rainfall data, soil type by region, current market demand, and typical harvest cycles to recommend the best herbs to plant in your next season, optimal planting windows, and expected yield ranges. Access these from 'AI Insights' on your Farmer dashboard.",
      },
      {
        q: "How do I get paid for a sale?",
        a: "Payments for large orders are processed through the platform's escrow module. When a buyer places an order, funds are held in escrow. Once you confirm delivery and the buyer confirms receipt, the funds are released to your account. For smaller spot purchases, direct bank transfer details can be shared through the secure messaging system.",
      },
    ],
  },
  {
    id: "researchers",
    icon: "🔬",
    title: "For Researchers",
    faqs: [
      {
        q: "How do I submit a clinical trial?",
        a: "Go to 'Research Hub' on your dashboard and click 'Submit New Trial'. Provide the trial title, herb(s) under study, principal investigator details, study design, participant count, ethics committee approval reference, and the primary and secondary endpoints. The AI will automatically generate an initial evidence score based on your submitted protocol.",
      },
      {
        q: "What is an AI Evidence Score?",
        a: "The AI Evidence Score (0–100) estimates the scientific strength of your trial based on study design (randomised controlled trials score highest), sample size, blinding status, endpoint clarity, and alignment with existing published literature on the herb. It is a screening tool — it does not replace peer review but helps pharma companies prioritise which research to engage with.",
      },
      {
        q: "How do I log patient outcomes?",
        a: "From an active trial record, click 'Log Outcome'. Enter anonymised patient identifiers, the treatment arm, dosage, duration, observed outcomes, adverse events (if any), and your assessment. All patient data is stored with row-level security — only you and collaborators you designate can view individual records.",
      },
      {
        q: "Can I collaborate with other researchers?",
        a: "Yes. From your trial record, open the 'Collaborators' tab and invite colleagues by email. Collaborators can view and add outcome data but cannot edit the core trial protocol without PI approval. Collaboration activity is fully audit-logged.",
      },
      {
        q: "How do pharma companies access my research?",
        a: "You control visibility. You can set a trial to Public (visible in the Research Hub marketplace), Institution Only (visible to your affiliated organisation), or Private (only you and collaborators). Public trials with high evidence scores are prominently featured and pharma companies can send licensing or partnership inquiries directly through the platform.",
      },
      {
        q: "What file formats are supported for uploading research documents?",
        a: "The platform accepts PDF, DOCX, and XLSX uploads up to 25 MB per file. Clinical protocols, ethics approvals, raw data sheets, and published papers can all be attached to a trial record. Files are stored securely in encrypted cloud storage.",
      },
    ],
  },
  {
    id: "pharma",
    icon: "🏭",
    title: "For Pharma Companies",
    faqs: [
      {
        q: "How do I use the AI Formulation Lab?",
        a: "Navigate to 'Formulation Lab' on your dashboard. Select one or more herbs from the database, specify the desired dosage form (tablet, capsule, syrup, tincture, cream, or injectable), target indication, and any excipient constraints. The AI — powered by Claude — will generate a detailed formulation proposal including ingredient ratios, manufacturing process steps, stability considerations, and a preliminary regulatory pathway note.",
      },
      {
        q: "Are the AI formulations ready to file with NAFDAC?",
        a: "AI formulations are starting points, not final submissions. They provide a scientifically grounded draft that your regulatory affairs team should review, validate through bench trials, and refine before filing. The platform's NAFDAC Compliance module can then help structure the dossier for submission.",
      },
      {
        q: "How does NAFDAC document generation work?",
        a: "In the Compliance module, select the submission type (new product registration, variation, renewal) and the product category. The AI will pre-fill applicable sections of the dossier based on your product data and flag sections requiring manual input. It tracks your document through NAFDAC's eight approval stages and sends reminders at each milestone.",
      },
      {
        q: "How do I source herbs from farmers?",
        a: "Open the 'Farm Marketplace' from your dashboard. Filter by herb name, region, minimum quantity, certifications, and price range. Click on a listing to view the farmer's profile, quality photos, and harvest history. Submit an inquiry with your desired quantity and offer price. The farmer will respond through the in-platform messaging system.",
      },
      {
        q: "Can I verify the quality of herbs before purchasing?",
        a: "Listings from verified farmers display a trust badge. You can request a physical sample (sample shipment costs agreed between parties) before committing to a bulk order. The platform also surfaces AI-generated quality indicators derived from the farmer's harvest history, region, and season.",
      },
      {
        q: "How do I manage multiple product pipelines?",
        a: "Your Pharma dashboard includes a Pipeline Kanban view where each product moves through stages: Concept → Formulation → Pre-clinical → Clinical → NAFDAC Filing → Approved. You can assign team members to each product, attach documents, set deadlines, and track progress at a glance.",
      },
    ],
  },
  {
    id: "export",
    icon: "🚢",
    title: "Export & Logistics",
    faqs: [
      {
        q: "How do I create an export listing?",
        a: "From the Export dashboard, click 'New Export Listing'. Specify the herb(s), total weight, packaging type, origin state, target destination country, and preferred Incoterms (EXW, FOB, CIF, etc.). The AI Customs Assistant will automatically attach the correct HS code and flag any destination-country import restrictions for the listed herb.",
      },
      {
        q: "How does the AI freight quote work?",
        a: "Once your listing is created, click 'Get Freight Quotes'. The AI considers shipment weight, dimensions, origin port (Apapa, Tin Can, or Onne), destination port, current carrier rate indices, and typical transit times to generate a ranked list of estimated freight options. Actual quotes from registered freight forwarders are also solicited in parallel.",
      },
      {
        q: "What is the escrow payment system?",
        a: "Escrow protects both buyer and seller in international transactions. When an order is confirmed, the buyer deposits funds into the platform's escrow account. Funds are released to the seller only after the buyer confirms receipt of goods in acceptable condition. Disputes are reviewed by the platform's logistics arbitration team within 5 business days.",
      },
      {
        q: "Which destination countries are supported?",
        a: "The platform supports exports to all 54 African Union member states, the United Kingdom, the European Union, the United States, Canada, India, and China. The AI Customs Assistant holds phytosanitary requirements and import permit data for all supported destinations. Additional countries can be requested via support.",
      },
      {
        q: "How do I track a shipment in transit?",
        a: "Attach a Bill of Lading or airway bill number to your export record. The platform integrates with major Nigerian freight forwarder tracking APIs to display live status updates. You and your buyer both receive automatic notifications at key milestones: departure from origin port, arrival at destination port, and customs clearance.",
      },
      {
        q: "What documents are generated for export?",
        a: "The Customs Assistant generates a pre-filled Phytosanitary Certificate (for NDA submission), Certificate of Origin, Commercial Invoice template, and Packing List. For EU-bound shipments it also produces the required Organic Equivalence Declaration where applicable. All documents are downloadable as PDF.",
      },
    ],
  },
  {
    id: "ai-features",
    icon: "🤖",
    title: "AI Features",
    faqs: [
      {
        q: "What is the AI Herb Assistant?",
        a: "The AI Herb Assistant is a conversational chatbot (powered by Claude) that answers questions about any of the 20+ herbs in the NaijaMed database. Ask it about active compounds, traditional uses, known drug interactions, dosage ranges, regional distribution, or harvest periods. It responds with references to the herb's database entry and, where available, links to published research.",
      },
      {
        q: "How accurate is the AI Herb Assistant?",
        a: "The assistant draws from a curated database of Nigerian medicinal herbs cross-referenced with PubMed literature and NAFDAC records. Accuracy is high for well-studied herbs (Moringa, Neem, African Basil), but more limited for rare or under-researched species. Always validate AI outputs with a qualified pharmacognosist or regulatory consultant before clinical or commercial use.",
      },
      {
        q: "What does the AI Customs Assistant do?",
        a: "The AI Customs Assistant helps exporters navigate international phytosanitary regulations, assign correct HS tariff codes to herbal products, identify required documentation per destination country, flag banned or restricted substances in target markets, and estimate import duty rates. It is updated quarterly with data from NAFDAC, NCS (Nigerian Customs Service), and WTO tariff schedules.",
      },
      {
        q: "What is Price Intelligence?",
        a: "Price Intelligence uses AI to analyse historical transaction data, current farm listings, global commodity markets for comparable botanicals, and demand signals from pharma companies to forecast herb prices over the next 30 and 90 days. Farmers use it to time sales; pharma companies use it to plan procurement budgets.",
      },
      {
        q: "Can I ask the AI to compare multiple herbs?",
        a: "Yes. In the AI Herb Assistant, type a comparative question such as 'Compare the anti-inflammatory properties of Moringa and African Basil' or 'Which herb has stronger evidence for diabetes management: Bitter Leaf or Guava Leaf?' The AI will structure a side-by-side comparison referencing the database entries for both herbs.",
      },
      {
        q: "Is my conversation with the AI private?",
        a: "Yes. Conversations with the AI assistants are tied to your account and are not shared with other users. Anonymised, aggregated usage patterns may be used to improve AI responses over time, but individual conversation content is never disclosed. You can delete your conversation history from Account Settings.",
      },
    ],
  },
  {
    id: "account-security",
    icon: "🔐",
    title: "Account & Security",
    faqs: [
      {
        q: "How do I change my password?",
        a: "Go to the top-right user menu → Account Settings → Security. Enter your current password, then your new password twice, and click Save. Passwords must be at least 8 characters and include a mix of uppercase letters, numbers, and symbols. After a password change you will be asked to re-authenticate on all other active sessions.",
      },
      {
        q: "What should I do if I forget my password?",
        a: "Click 'Forgot Password?' on the login screen. Enter your registered email address and we will send a secure reset link valid for 30 minutes. Check your spam folder if the email does not arrive within 5 minutes. If you no longer have access to your registered email, contact support@nigerflora.com with proof of identity.",
      },
      {
        q: "Is two-factor authentication (2FA) available?",
        a: "Yes. Enable 2FA from Account Settings → Security → Two-Factor Authentication. We support authenticator apps (Google Authenticator, Authy) and SMS OTP. We strongly recommend enabling 2FA, especially for Admin and Pharma Company accounts that access sensitive regulatory documents.",
      },
      {
        q: "How do I update my profile or contact information?",
        a: "Navigate to Account Settings → Profile. You can update your display name, phone number, organisation name, profile picture, and notification preferences. Email address changes require re-verification via a confirmation link sent to the new address.",
      },
      {
        q: "How do I deactivate or delete my account?",
        a: "Account deactivation (temporary suspension) can be done from Account Settings → Danger Zone → Deactivate Account. Permanent deletion requires contacting support@nigerflora.com — we will confirm your identity and process the request within 14 days in line with data protection obligations. Note that research and transaction records linked to your account may be retained in anonymised form for regulatory compliance.",
      },
      {
        q: "How do I contact the platform administrator?",
        a: "For technical support, email support@nigerflora.com or use the in-app 'Help & Feedback' button at the bottom of any dashboard page. For regulatory or compliance enquiries, email compliance@nigerflora.com. For partnership or media enquiries, contact partnerships@nigerflora.com. Our support team responds within 1–2 business days (Lagos time, WAT).",
      },
    ],
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function AccordionItem({
  faq,
  isOpen,
  onToggle,
}: {
  faq: FAQ;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border border-forest-100 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left bg-white hover:bg-forest-50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-forest-400 focus:ring-inset"
        aria-expanded={isOpen}
      >
        <span className="font-medium text-forest-700 text-sm md:text-base leading-snug">
          {faq.q}
        </span>
        <span
          className={`flex-shrink-0 w-6 h-6 rounded-full bg-forest-100 flex items-center justify-center text-forest-600 text-xs font-bold transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>
      {isOpen && (
        <div className="px-5 py-4 bg-forest-50 border-t border-forest-100">
          <p className="text-gray-600 text-sm leading-relaxed">{faq.a}</p>
        </div>
      )}
    </div>
  );
}

function SectionPanel({
  section,
  searchActive,
  matchedFaqs,
}: {
  section: Section;
  searchActive: boolean;
  matchedFaqs: FAQ[];
}) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [sectionOpen, setSectionOpen] = useState(false);

  const visibleFaqs = searchActive ? matchedFaqs : section.faqs;

  if (searchActive && visibleFaqs.length === 0) return null;

  const isExpanded = searchActive || sectionOpen;

  return (
    <div className="card overflow-hidden">
      {/* Section header */}
      <button
        onClick={() => setSectionOpen((v) => !v)}
        className="w-full flex items-center gap-4 text-left focus:outline-none focus:ring-2 focus:ring-forest-400 focus:ring-inset rounded-lg"
        aria-expanded={isExpanded}
      >
        <div className="w-11 h-11 rounded-xl bg-forest-600 flex items-center justify-center text-xl flex-shrink-0">
          {section.icon}
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-bold text-forest-700">{section.title}</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {visibleFaqs.length}{" "}
            {visibleFaqs.length === 1 ? "article" : "articles"}
            {searchActive && visibleFaqs.length < section.faqs.length
              ? ` matched of ${section.faqs.length}`
              : ""}
          </p>
        </div>
        <span
          className={`flex-shrink-0 w-7 h-7 rounded-full border border-forest-200 bg-forest-50 flex items-center justify-center text-forest-500 text-xs transition-transform duration-200 ${
            isExpanded ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>

      {/* FAQs */}
      {isExpanded && (
        <div className="mt-4 space-y-2">
          {visibleFaqs.map((faq, i) => (
            <AccordionItem
              key={i}
              faq={faq}
              isOpen={openIndex === i}
              onToggle={() => setOpenIndex(openIndex === i ? null : i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Help() {
  const [query, setQuery] = useState("");

  const normalised = query.trim().toLowerCase();

  const filteredSections = useMemo<{ section: Section; matched: FAQ[] }[]>(() => {
    return SECTIONS.map((section) => {
      if (!normalised) return { section, matched: [] };
      const matched = section.faqs.filter(
        (faq) =>
          faq.q.toLowerCase().includes(normalised) ||
          faq.a.toLowerCase().includes(normalised) ||
          section.title.toLowerCase().includes(normalised)
      );
      return { section, matched };
    });
  }, [normalised]);

  const totalMatches = filteredSections.reduce((sum, { matched }) => sum + matched.length, 0);
  const searchActive = normalised.length > 0;

  return (
    <div className="min-h-screen bg-cream">
      {/* ── Top Nav ── */}
      <nav className="bg-forest-600 text-white px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-md">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">🌿</span>
          <div>
            <div className="font-bold text-lg text-gold-300">NaijaMed AI</div>
            <div className="text-xs text-forest-200 hidden sm:block">
              From Soil to Science to Pharmacy
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="text-forest-100 hover:text-white text-sm font-medium px-3 py-1.5 rounded-md hover:bg-forest-500 transition-colors"
          >
            ← Home
          </Link>
          <Link to="/login" className="btn-secondary text-sm px-4 py-2">
            Sign In
          </Link>
        </div>
      </nav>

      {/* ── Hero / Search Banner ── */}
      <section className="bg-hero-pattern text-white">
        <div className="max-w-4xl mx-auto px-6 py-16 text-center">
          <div className="inline-flex items-center gap-2 bg-forest-700/60 text-gold-300 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            📖 Knowledge Base &amp; Help Centre
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            How can we <span className="text-gold-300">help you?</span>
          </h1>
          <p className="text-forest-100 text-lg mb-10 max-w-2xl mx-auto">
            Search our articles or browse by topic below. Find step-by-step guidance for every
            role on the platform.
          </p>

          {/* Search bar */}
          <div className="relative max-w-2xl mx-auto">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg pointer-events-none select-none">
              🔍
            </span>
            <input
              type="search"
              placeholder="Search articles… e.g. 'how to list herbs', 'NAFDAC', 'escrow'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-12 pr-10 py-4 rounded-xl bg-white text-forest-900 placeholder-gray-400 text-base focus:outline-none focus:ring-4 focus:ring-gold-400/50 shadow-lg"
            />
            {searchActive && (
              <button
                onClick={() => setQuery("")}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-2xl leading-none focus:outline-none"
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </div>

          {/* Search result summary */}
          {searchActive && (
            <p className="mt-4 text-forest-200 text-sm">
              {totalMatches === 0
                ? "No articles matched your search. Try different keywords or browse by topic below."
                : `Found ${totalMatches} article${totalMatches !== 1 ? "s" : ""} matching "${query}"`}
            </p>
          )}
        </div>
      </section>

      {/* ── Quick Start Cards ── */}
      {!searchActive && (
        <section className="max-w-7xl mx-auto px-6 py-14">
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-bold text-forest-700 mb-2">
              Quick Start by Role
            </h2>
            <p className="text-gray-500 text-base">
              Jump straight to the guide for your role on the platform.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5">
            {QUICK_START_CARDS.map((card) => (
              <div key={card.role} className="card-hover flex flex-col gap-3">
                <div className="w-12 h-12 rounded-xl bg-forest-600 flex items-center justify-center text-2xl flex-shrink-0">
                  {card.icon}
                </div>
                <div>
                  <span className="badge-green text-xs mb-2 inline-block">{card.role}</span>
                  <p className="text-gray-500 text-xs leading-relaxed">{card.desc}</p>
                </div>
                <ol className="space-y-1 mt-auto">
                  {card.steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-forest-100 text-forest-700 text-[10px] font-bold flex items-center justify-center mt-0.5">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
                <Link
                  to={card.link}
                  className="btn-primary text-xs px-3 py-2 text-center mt-2 block"
                >
                  Get Started →
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── FAQ Sections ── */}
      <section className="max-w-4xl mx-auto px-6 pb-16" id="faq">
        {!searchActive && (
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-bold text-forest-700 mb-2">
              Browse by Topic
            </h2>
            <p className="text-gray-500 text-base">Click a section to expand its articles.</p>
          </div>
        )}

        <div className="space-y-4">
          {filteredSections.map(({ section, matched }) => (
            <SectionPanel
              key={section.id}
              section={section}
              searchActive={searchActive}
              matchedFaqs={matched}
            />
          ))}
        </div>

        {/* No results state */}
        {searchActive && totalMatches === 0 && (
          <div className="card text-center py-16 mt-6">
            <div className="text-5xl mb-4">🌿</div>
            <h3 className="font-bold text-forest-700 text-lg mb-2">No results found</h3>
            <p className="text-gray-500 text-sm max-w-sm mx-auto mb-6">
              We couldn&apos;t find any articles matching <strong>&ldquo;{query}&rdquo;</strong>.
              Try broader keywords or contact support.
            </p>
            <button onClick={() => setQuery("")} className="btn-outline text-sm">
              Clear Search
            </button>
          </div>
        )}
      </section>

      {/* ── Stats Bar ── */}
      {!searchActive && (
        <section className="bg-forest-600 text-white py-10">
          <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {(
              [
                ["7", "Help Topics"],
                ["42", "Knowledge Articles"],
                ["5", "User Roles Covered"],
                ["24/7", "AI Assistance"],
              ] as [string, string][]
            ).map(([val, label]) => (
              <div key={label}>
                <div className="font-bold text-3xl text-gold-300">{val}</div>
                <div className="text-forest-200 text-sm font-medium mt-1">{label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Contact / Support Section ── */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold text-forest-700 mb-2">
            Still need help?
          </h2>
          <p className="text-gray-500 text-base max-w-xl mx-auto">
            Our support team is based in Lagos and responds within 1–2 business days (WAT). For
            urgent regulatory matters, use the compliance channel.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* General Support */}
          <div className="card flex flex-col items-center text-center gap-3 py-8">
            <div className="w-14 h-14 bg-forest-100 rounded-full flex items-center justify-center text-3xl">
              💬
            </div>
            <h3 className="font-bold text-forest-700 text-base">General Support</h3>
            <p className="text-gray-500 text-sm leading-relaxed">
              Technical issues, account problems, or general platform questions.
            </p>
            <a
              href="mailto:support@nigerflora.com"
              className="btn-primary text-sm px-4 py-2 mt-auto"
            >
              support@nigerflora.com
            </a>
          </div>

          {/* Compliance */}
          <div className="card flex flex-col items-center text-center gap-3 py-8 border-gold-200 bg-gold-50/40">
            <div className="w-14 h-14 bg-gold-100 rounded-full flex items-center justify-center text-3xl">
              📋
            </div>
            <h3 className="font-bold text-forest-700 text-base">Compliance &amp; Regulatory</h3>
            <p className="text-gray-500 text-sm leading-relaxed">
              NAFDAC documentation, export permits, and regulatory advisory support.
            </p>
            <a
              href="mailto:compliance@nigerflora.com"
              className="btn-secondary text-sm px-4 py-2 mt-auto"
            >
              compliance@nigerflora.com
            </a>
          </div>

          {/* Partnerships */}
          <div className="card flex flex-col items-center text-center gap-3 py-8">
            <div className="w-14 h-14 bg-forest-100 rounded-full flex items-center justify-center text-3xl">
              🤝
            </div>
            <h3 className="font-bold text-forest-700 text-base">Partnerships &amp; Media</h3>
            <p className="text-gray-500 text-sm leading-relaxed">
              Business development, research collaborations, press, and media enquiries.
            </p>
            <a
              href="mailto:partnerships@nigerflora.com"
              className="btn-outline text-sm px-4 py-2 mt-auto"
            >
              partnerships@nigerflora.com
            </a>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-10 rounded-xl bg-forest-50 border border-forest-100 p-5 flex gap-4 items-start">
          <span className="text-2xl flex-shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-forest-700 mb-1">Important Disclaimer</p>
            <p className="text-xs text-gray-500 leading-relaxed">
              AI-generated content on this platform — including herb information, formulation
              proposals, customs guidance, and compliance documents — is provided for informational
              purposes only. It does not constitute legal, medical, or regulatory advice. Always
              consult a certified NAFDAC regulatory consultant, licensed pharmacist, or qualified
              legal professional before making clinical, commercial, or regulatory decisions.
            </p>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-forest-800 text-forest-300 py-8 text-center text-sm">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-xl">🌿</span>
          <span className="text-gold-300 font-semibold">NaijaMed AI</span>
        </div>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-forest-400 text-xs mb-3">
          <Link to="/" className="hover:text-forest-200 transition-colors">
            Home
          </Link>
          <Link to="/login" className="hover:text-forest-200 transition-colors">
            Sign In
          </Link>
          <Link to="/register" className="hover:text-forest-200 transition-colors">
            Register
          </Link>
          <a
            href="mailto:support@nigerflora.com"
            className="hover:text-forest-200 transition-colors"
          >
            Support
          </a>
        </div>
        <p>
          © {new Date().getFullYear()} NigerFlora BioSciences · Empowering Nigerian Herbal
          Medicine
        </p>
        <p className="text-forest-500 text-xs mt-2">
          AI guidance is informational only — always consult a certified NAFDAC regulatory
          consultant.
        </p>
      </footer>
    </div>
  );
}
