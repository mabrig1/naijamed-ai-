import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, ProgressBar, Spinner } from "../components/Layout";

type Dimension = {
  key: string;
  label: string;
  weight: number;
  earned: number;
  completion: number;
  status: "strong" | "developing" | "gap";
  guidance: string;
};

type Lens = {
  label: string;
  verified_on: string;
  sources: Array<{
    organization: string;
    label: string;
    url: string;
    criteria: string[];
  }>;
  notice: string;
};

type Profile = {
  funder_lens: "cross_funder" | "horizon_europe" | "nih" | "wellcome";
  innovation_case?: string;
  global_relevance?: string;
  rigor_feasibility?: string;
  impact_pathway?: string;
  institutional_capacity?: string;
  ethics_governance?: string;
  data_open_science?: string;
  equity_capacity_building?: string;
  sustainability_scale?: string;
  policy_translation?: string;
  monitoring_evaluation?: string;
  risk_management?: string;
  cofunding_leverage?: string;
  impact_metrics?: string[];
  capacity_outputs?: string[];
  data_management_commitments?: string[];
  sdg_alignment?: string[];
  keywords?: string[];
};

type Readiness = {
  score: number;
  dimensions: Dimension[];
  priority_gaps: string[];
  lens: Lens;
  notice: string;
};

type ProfilePayload = {
  project_id: string;
  profile: Profile;
  readiness: Readiness;
  lens: Lens;
};

type Room = {
  id: string;
  recipient_label?: string | null;
  expires_at?: string | null;
  revoked: boolean;
  access_count: number;
  last_accessed_at?: string | null;
  created_at?: string | null;
  readiness_score?: number | null;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function lines(value?: string[]) {
  return (value ?? []).join("\n");
}

function list(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

const EMPTY: Profile = {
  funder_lens: "cross_funder",
  innovation_case: "",
  global_relevance: "",
  rigor_feasibility: "",
  impact_pathway: "",
  institutional_capacity: "",
  ethics_governance: "",
  data_open_science: "",
  equity_capacity_building: "",
  sustainability_scale: "",
  policy_translation: "",
  monitoring_evaluation: "",
  risk_management: "",
  cofunding_leverage: "",
  impact_metrics: [],
  capacity_outputs: [],
  data_management_commitments: [],
  sdg_alignment: [],
  keywords: [],
};

export default function FormularyFunderStudio() {
  const { projectId = "" } = useParams();
  const [profile, setProfile] = useState<Profile>(EMPTY);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [lens, setLens] = useState<Lens | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [roomForm, setRoomForm] = useState({
    recipient_label: "",
    expires_in_days: "14",
    include_budget: true,
    include_partners: true,
    include_milestones: true,
    note: "",
  });

  async function refresh() {
    const [{ data: profileData }, { data: roomsData }] = await Promise.all([
      api.get<ProfilePayload>(`/api/formulary/grants/projects/${projectId}/funder-profile`),
      api.get<{ rooms: Room[] }>(`/api/formulary/grants/projects/${projectId}/funder-rooms`),
    ]);
    setProfile({ ...EMPTY, ...profileData.profile });
    setReadiness(profileData.readiness);
    setLens(profileData.lens);
    setRooms(roomsData.rooms);
  }

  useEffect(() => {
    refresh()
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function setText(key: keyof Profile, value: string) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function loadNexusNarrative() {
    setProfile({
      funder_lens: "cross_funder",
      innovation_case: "NEXUS-AMR Africa is designed as an integrated translational platform rather than a single prevalence study. It connects One Health surveillance, pathogen genomics, climate/environmental intelligence, implementation research and a disciplined antimicrobial-discovery pipeline. The innovation lies in generating interoperable evidence across sectors and moving from description toward prediction, intervention and translational research.",
      global_relevance: "The programme addresses antimicrobial resistance as a cross-border health, food-system and environmental challenge while generating evidence from an underrepresented African setting. Nsukka becomes a scientifically useful living laboratory where human, animal, food and environmental systems can be studied together and where locally led research can contribute to global AMR knowledge, methods and intervention design.",
      rigor_feasibility: "Delivery will be staged through independently governed work packages with predefined protocols, quality-control procedures, power calculations, laboratory SOPs, data standards, milestone gates and external scientific review. High-risk translational components will use go/no-go criteria so the programme does not depend on every exploratory activity succeeding.",
      impact_pathway: "Near-term outputs include a One Health surveillance network, curated datasets, genomic maps, trained researchers, predictive models and evaluated stewardship interventions. Medium-term outcomes include improved surveillance practice, stronger institutional research capacity, policy-relevant evidence and validated antimicrobial research leads. Long-term impact depends on adoption by health, veterinary, agricultural and research partners and successful follow-on translational investment.",
      institutional_capacity: "UNN is proposed as the African coordinating hub. The final application should document facilities, named investigators, time commitments, governance authority, laboratories, field access, data infrastructure and institutional support. International partners should fill clearly defined capability gaps rather than duplicate local leadership.",
      ethics_governance: "Human, animal, environmental and biological-resource components will proceed only under applicable ethics, biosafety, data-protection and institutional approvals. Governance should include a programme steering committee, independent scientific advisory input, data-access rules, conflict-of-interest management and transparent decision rights across the consortium.",
      data_open_science: "The programme should use FAIR-aligned data stewardship where compatible with consent, privacy, biosafety, national rules and legitimate IP interests. Protocols, metadata standards, analysis code and suitable de-identified outputs should be shared through appropriate repositories, with controlled access for sensitive genomic, participant or commercially relevant data.",
      equity_capacity_building: "The consortium should place African scientific leadership, equitable partnership and durable capacity at the centre of delivery. Training pathways should include postgraduate researchers, postdoctoral scientists, laboratory teams, data scientists and research managers, with transparent authorship, mentorship, mobility and leadership opportunities.",
      sustainability_scale: "Infrastructure, datasets, biobanking workflows, analytic pipelines and trained personnel should be designed for continued use after the first award. Successful surveillance and intervention components should have defined pathways for adoption by institutions and public agencies, while promising discovery outputs should have staged routes to follow-on translational funding or responsible partnership.",
      policy_translation: "Policy and implementation partners should be engaged from project design rather than only at dissemination. The project should convert findings into decision briefs, implementation tools, surveillance feedback and structured dialogues with health, veterinary, agricultural and environmental stakeholders.",
      monitoring_evaluation: "Each work package should have output, outcome, quality and capacity indicators with named owners, verification sources and review dates. Consortium-level monitoring should track scientific delivery, recruitment/sampling targets where applicable, budget execution, partner commitments, training outcomes, data quality and uptake of policy/implementation outputs.",
      risk_management: "Key risks include scope inflation, weak data quality, laboratory bottlenecks, delayed approvals, partner under-delivery, insufficient sequencing capacity, model overfitting, failure of discovery leads and IP disputes. Each should have a named owner, trigger, mitigation action and fallback pathway, with high-risk science managed through milestone-based continuation decisions.",
      cofunding_leverage: "The grant should be presented as a platform that unlocks additional value: institutional in-kind support, specialist partner capability, future translational awards, industry co-development where appropriate, regional network expansion and reusable research infrastructure. Any claimed co-funding or in-kind contribution must be documented before submission.",
      impact_metrics: [
        "Operational One Health surveillance sites and sectors connected",
        "Quality-controlled isolates/samples and genomic records generated",
        "Peer-reviewed outputs and reusable protocols/software",
        "Researchers trained with documented competency gains",
        "Policy/implementation products adopted or formally considered",
        "Validated intervention effects and cost-effectiveness outputs",
        "Promising antimicrobial research leads passing predefined gates",
      ],
      capacity_outputs: [
        "Postgraduate and postdoctoral training positions",
        "Genomics/bioinformatics and data-management capability",
        "Governed biobank and reproducible analysis pipelines",
        "International mentorship and co-leadership structures",
        "Grant-management and research-governance capability",
      ],
      data_management_commitments: [
        "Project-wide data management plan",
        "Role-based access to sensitive data",
        "Version-controlled analysis code",
        "Repository deposition where ethically and legally appropriate",
        "Documented metadata, provenance, retention and reuse rules",
      ],
      sdg_alignment: ["SDG 3", "SDG 9", "SDG 17"],
      keywords: ["antimicrobial resistance", "One Health", "genomics", "climate-health", "drug discovery", "implementation science", "Africa"],
    });
    setMessage("NEXUS-AMR funder narrative loaded. Verify institutional claims and add evidence before sharing.");
  }

  async function save() {
    setAction("save");
    setError("");
    setMessage("");
    try {
      const payload = {
        ...profile,
        impact_metrics: profile.impact_metrics ?? [],
        capacity_outputs: profile.capacity_outputs ?? [],
        data_management_commitments: profile.data_management_commitments ?? [],
        sdg_alignment: profile.sdg_alignment ?? [],
        keywords: profile.keywords ?? [],
      };
      const { data } = await api.put<any>(`/api/formulary/grants/projects/${projectId}/funder-profile`, payload);
      setProfile({ ...EMPTY, ...data.funder_profile });
      setReadiness(data.funder_readiness);
      setMessage("Funder-facing dossier saved and readiness lens recalculated.");
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function createRoom() {
    setAction("share");
    setError("");
    setMessage("");
    setShareUrl("");
    try {
      const { data } = await api.post<{ share_path: string; expires_at: string; readiness: Readiness }>(
        `/api/formulary/grants/projects/${projectId}/funder-rooms`,
        {
          recipient_label: roomForm.recipient_label || null,
          expires_in_days: Number(roomForm.expires_in_days),
          include_budget: roomForm.include_budget,
          include_partners: roomForm.include_partners,
          include_milestones: roomForm.include_milestones,
          note: roomForm.note || null,
        },
      );
      const url = `${window.location.origin}${data.share_path}`;
      setShareUrl(url);
      try { await navigator.clipboard.writeText(url); } catch { /* show URL */ }
      setMessage(`Frozen funder room created and copied. Expires ${new Date(data.expires_at).toLocaleString()}.`);
      await refresh();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function revoke(roomId: string) {
    setAction(roomId);
    try {
      await api.post(`/api/formulary/grants/projects/${projectId}/funder-rooms/${roomId}/revoke`);
      setMessage("Funder room revoked.");
      await refresh();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  if (error && !readiness) return <PageError message={error} />;

  const field = (
    key: keyof Profile,
    label: string,
    placeholder: string,
  ) => (
    <div>
      <label className="label">{label}</label>
      <textarea
        className="input min-h-32"
        value={String(profile[key] ?? "")}
        onChange={(e) => setText(key, e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">International funder dossier</div>
            <h1 className="mt-3 text-4xl font-bold">Turn the research project into a reviewer-ready investment case.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Build the narrative a funder needs to judge importance, feasibility, impact, capability and research environment—then share a frozen due-diligence room without exposing your private IP ledger.
            </p>
          </div>
          <div className="min-w-56 rounded-2xl border border-white/10 bg-white/10 p-5">
            <div className="text-xs uppercase tracking-wide text-forest-200">Funder-facing completeness</div>
            <div className="mt-2 text-4xl font-bold text-gold-300">{readiness?.score ?? 0}%</div>
            <div className="mt-3"><ProgressBar value={readiness?.score ?? 0} /></div>
            <div className="mt-2 text-[11px] leading-4 text-forest-200">Not a funding probability.</div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link className="btn-outline" to="/formulary/grants">← Grant Project Studio</Link>
        <Link className="btn-outline" to="/formulary/copilot">Grant Copilot</Link>
        <button className="btn-outline" onClick={loadNexusNarrative}>Load NEXUS-AMR funder narrative</button>
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-forest-800">Funder lens</h2>
                <p className="mt-1 text-sm text-gray-500">Choose a preparation lens, then verify the live call before submission.</p>
              </div>
              <select className="input max-w-xs" value={profile.funder_lens} onChange={(e) => setProfile((v) => ({ ...v, funder_lens: e.target.value as Profile["funder_lens"] }))}>
                <option value="cross_funder">Cross-funder international lens</option>
                <option value="horizon_europe">Horizon Europe</option>
                <option value="nih">NIH</option>
                <option value="wellcome">Wellcome</option>
              </select>
            </div>
            {lens && (
              <div className="mt-5 rounded-2xl bg-cream p-4">
                <div className="font-semibold text-forest-800">{lens.label}</div>
                <div className="mt-1 text-xs text-gray-500">Criteria references verified in the app on {lens.verified_on}. Re-check the current call text.</div>
                <div className="mt-3 space-y-2">
                  {lens.sources.map((source) => (
                    <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="block rounded-xl bg-white p-3 text-sm hover:ring-1 hover:ring-forest-200">
                      <div className="font-semibold">{source.organization} — {source.label}</div>
                      <div className="mt-1 text-xs text-gray-500">{source.criteria.join(" · ")}</div>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="card space-y-5">
            <h2 className="text-xl font-bold text-forest-800">Reviewer narrative</h2>
            {field("innovation_case", "Innovation / conceptual advance", "What is genuinely new, and why is it a meaningful advance rather than a collection of activities?")}
            {field("global_relevance", "Global relevance", "Why does this matter beyond the immediate study site, and what globally transferable knowledge or capability will result?")}
            {field("rigor_feasibility", "Rigor & feasibility", "Methods, quality controls, dependencies, go/no-go gates, preliminary evidence and feasibility safeguards.")}
            {field("impact_pathway", "Impact pathway", "How do activities become outputs, outcomes, adoption, policy/clinical/industry value and longer-term impact?")}
            {field("institutional_capacity", "Institutional capacity & environment", "Named capability, facilities, protected time, research support, infrastructure and complementary partner strengths.")}
            {field("ethics_governance", "Ethics & governance", "Ethics, biosafety, decision rights, advisory structures, conflicts, data access and responsible research safeguards.")}
            {field("data_open_science", "Data, reproducibility & open science", "FAIR principles, repositories, metadata, code, access controls, reproducibility and legitimate limits on sharing.")}
            {field("equity_capacity_building", "Equity, capacity building & research culture", "Local leadership, equitable partnership, training, mentorship, authorship and durable institutional capacity.")}
            {field("sustainability_scale", "Sustainability & scale", "What remains after the grant and how successful outputs move to wider adoption or follow-on translation.")}
            {field("policy_translation", "Policy / implementation translation", "Who must act on the evidence, how they are engaged, and what concrete implementation products will be delivered.")}
            {field("monitoring_evaluation", "Monitoring & evaluation", "KPIs, verification sources, outcome indicators, review cadence and who owns corrective action.")}
            {field("risk_management", "Risk management", "Scientific, operational, consortium, ethical, financial and translational risks plus triggers and fallback paths.")}
            {field("cofunding_leverage", "Leverage & additionality", "What institutional, partner, follow-on or co-investment value becomes possible because this award exists.")}

            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <label className="label">Impact metrics — one per line</label>
                <textarea className="input min-h-40" value={lines(profile.impact_metrics)} onChange={(e) => setProfile((v) => ({ ...v, impact_metrics: list(e.target.value) }))} />
              </div>
              <div>
                <label className="label">Capacity outputs — one per line</label>
                <textarea className="input min-h-40" value={lines(profile.capacity_outputs)} onChange={(e) => setProfile((v) => ({ ...v, capacity_outputs: list(e.target.value) }))} />
              </div>
              <div>
                <label className="label">Data/open-science commitments — one per line</label>
                <textarea className="input min-h-36" value={lines(profile.data_management_commitments)} onChange={(e) => setProfile((v) => ({ ...v, data_management_commitments: list(e.target.value) }))} />
              </div>
              <div>
                <label className="label">SDG alignment — one per line</label>
                <textarea className="input min-h-36" value={lines(profile.sdg_alignment)} onChange={(e) => setProfile((v) => ({ ...v, sdg_alignment: list(e.target.value) }))} placeholder={"SDG 3\nSDG 9\nSDG 17"} />
              </div>
            </div>

            <button className="btn-primary w-full" disabled={action === "save"} onClick={save}>
              {action === "save" ? "Saving…" : "Save funder dossier & recalculate"}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Funder readiness lens</h2>
            <p className="mt-1 text-xs leading-5 text-gray-500">{readiness?.notice}</p>
            <div className="mt-5 space-y-3">
              {readiness?.dimensions.map((item) => (
                <div key={item.key} className="rounded-2xl border border-gray-100 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-gray-900">{item.label}</div>
                    <span className={`rounded-full px-2 py-1 text-xs font-bold ${item.status === "strong" ? "bg-forest-50 text-forest-700" : item.status === "developing" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>{item.completion}%</span>
                  </div>
                  <div className="mt-3"><ProgressBar value={item.completion} /></div>
                  <p className="mt-2 text-xs leading-5 text-gray-500">{item.guidance}</p>
                </div>
              ))}
            </div>
            {!!readiness?.priority_gaps.length && (
              <div className="mt-5 rounded-2xl bg-amber-50 p-4">
                <div className="font-semibold text-amber-800">Priority before sharing</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-800">
                  {readiness.priority_gaps.map((gap) => <li key={gap}>{gap}</li>)}
                </ul>
              </div>
            )}
          </div>

          <div className="card border border-gold-200">
            <h2 className="text-xl font-bold text-forest-800">Create Due-Diligence Room</h2>
            <p className="mt-2 text-sm leading-6 text-gray-500">Creates a frozen, expiring, read-only snapshot. Your IP register, disclosure history and private emails are not included.</p>
            <div className="mt-4 space-y-3">
              <input className="input" placeholder="Recipient / funder label" value={roomForm.recipient_label} onChange={(e) => setRoomForm((v) => ({ ...v, recipient_label: e.target.value }))} />
              <select className="input" value={roomForm.expires_in_days} onChange={(e) => setRoomForm((v) => ({ ...v, expires_in_days: e.target.value }))}>
                <option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option>
              </select>
              <textarea className="input min-h-20" placeholder="Optional context for the recipient" value={roomForm.note} onChange={(e) => setRoomForm((v) => ({ ...v, note: e.target.value }))} />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={roomForm.include_budget} onChange={(e) => setRoomForm((v) => ({ ...v, include_budget: e.target.checked }))} /> Include project/WP budgets</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={roomForm.include_partners} onChange={(e) => setRoomForm((v) => ({ ...v, include_partners: e.target.checked }))} /> Include consortium partners</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={roomForm.include_milestones} onChange={(e) => setRoomForm((v) => ({ ...v, include_milestones: e.target.checked }))} /> Include milestones</label>
              <button className="btn-primary w-full" disabled={action === "share"} onClick={createRoom}>{action === "share" ? "Creating secure room…" : "Create frozen funder room"}</button>
            </div>
            {shareUrl && (
              <div className="mt-4 rounded-xl bg-forest-50 p-3 text-xs text-forest-800">
                <div className="font-semibold">Share this link now</div>
                <div className="mt-1 break-all">{shareUrl}</div>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-lg font-bold text-forest-800">Shared funder rooms</h2>
            <div className="mt-4 space-y-3">
              {rooms.length ? rooms.map((room) => (
                <div key={room.id} className="rounded-xl border border-gray-100 p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <strong>{room.recipient_label || "Controlled recipient"}</strong>
                    <span className={`text-xs font-semibold ${room.revoked ? "text-red-700" : "text-forest-700"}`}>{room.revoked ? "Revoked" : "Active"}</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">Views: {room.access_count} · Readiness snapshot: {room.readiness_score ?? "—"}%</div>
                  <div className="mt-1 text-xs text-gray-500">Expires: {room.expires_at ? new Date(room.expires_at).toLocaleString() : "—"}</div>
                  {!room.revoked && <button className="btn-outline mt-3 text-xs" disabled={action === room.id} onClick={() => revoke(room.id)}>Revoke room</button>}
                </div>
              )) : <p className="text-sm text-gray-400">No funder room has been shared yet.</p>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
