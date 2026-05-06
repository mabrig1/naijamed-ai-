import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useHerbList } from "../../hooks/useHerbs";
import { useSubmitTrial, useLogOutcome } from "../../hooks/useResearch";
import { Spinner, PageError } from "../../components/Layout";
import type { AgeGroup, Sex, OutcomeResult } from "../../types";

const PHASES = ["Phase I", "Phase II", "Phase III", "Phase IV", "Observational", "Review"];

export default function SubmitTrial() {
  const navigate = useNavigate();
  const location = useLocation();
  const prefillHerbId = (location.state as { herbId?: number })?.herbId;

  const { data: herbs } = useHerbList({ limit: 100 });
  const submitMut = useSubmitTrial();
  const outcomeMut = useLogOutcome();

  // Trial fields
  const [herbId, setHerbId]         = useState(prefillHerbId?.toString() ?? "");
  const [title, setTitle]           = useState("");
  const [abstract, setAbstract]     = useState("");
  const [phase, setPhase]           = useState("");
  const [methodology, setMethodology] = useState("");
  const [patientCount, setPatientCount] = useState("");
  const [startDate, setStartDate]   = useState("");
  const [endDate, setEndDate]       = useState("");
  const [findings, setFindings]     = useState("");
  const [doi, setDoi]               = useState("");

  // Outcome fields (optional section)
  const [showOutcome, setShowOutcome] = useState(false);
  const [ageGroup, setAgeGroup]     = useState<AgeGroup>("adult");
  const [sex, setSex]               = useState<Sex>("not_disclosed");
  const [condition, setCondition]   = useState("");
  const [dosage, setDosage]         = useState("");
  const [duration, setDuration]     = useState("");
  const [outcome, setOutcome]       = useState<OutcomeResult>("improved");
  const [adverseDetails, setAdverseDetails] = useState("");

  const [trialId, setTrialId] = useState<number | null>(null);

  async function handleSubmitTrial(e: React.FormEvent) {
    e.preventDefault();
    const res = await submitMut.mutateAsync({
      herb_id: Number(herbId),
      title,
      abstract: abstract || undefined,
      study_phase: phase || undefined,
      methodology: methodology || undefined,
      patient_count: patientCount ? Number(patientCount) : undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      findings: findings || undefined,
      publication_doi: doi || undefined,
    });
    setTrialId(res.id);
    if (!showOutcome) navigate(`/research/trials/${res.id}`);
  }

  async function handleLogOutcome() {
    if (!trialId || !herbId) return;
    await outcomeMut.mutateAsync({
      herb_id: Number(herbId),
      trial_id: trialId,
      age_group: ageGroup,
      sex,
      condition_treated: condition,
      dosage_used: dosage || undefined,
      duration_days: duration ? Number(duration) : undefined,
      outcome,
      adverse_details: adverseDetails || undefined,
    });
    navigate(`/research/trials/${trialId}`);
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">📝 Submit Clinical Trial</h1>
        <p className="text-forest-200 text-sm mt-1">
          Contribute to the Nigerian herbal medicine evidence base. All patient data is anonymized.
        </p>
      </div>

      {!trialId ? (
        <div className="card">
          <form onSubmit={handleSubmitTrial} className="space-y-5">
            <div>
              <label className="label">Herb Under Study <span className="text-red-500">*</span></label>
              <select className="select" value={herbId} onChange={(e) => setHerbId(e.target.value)} required>
                <option value="">— Select a herb —</option>
                {herbs?.map((h) => <option key={h.id} value={h.id}>{h.name_english}{h.scientific_name ? ` (${h.scientific_name})` : ""}</option>)}
              </select>
            </div>

            <div>
              <label className="label">Trial Title <span className="text-red-500">*</span></label>
              <input className="input" placeholder="e.g. Efficacy of Moringa oleifera in Type 2 Diabetes Management"
                value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>

            <div>
              <label className="label">Abstract <span className="text-gray-400">(optional)</span></label>
              <textarea className="input min-h-28 resize-none" rows={4}
                placeholder="Brief summary of the study background, methods, and key findings…"
                value={abstract} onChange={(e) => setAbstract(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Study Phase</label>
                <select className="select" value={phase} onChange={(e) => setPhase(e.target.value)}>
                  <option value="">— Select —</option>
                  {PHASES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Participant Count</label>
                <input type="number" min="1" className="input" placeholder="e.g. 120"
                  value={patientCount} onChange={(e) => setPatientCount(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="label">Methodology</label>
              <input className="input" placeholder="e.g. Double-blind RCT, placebo-controlled"
                value={methodology} onChange={(e) => setMethodology(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Start Date</label>
                <input type="date" className="input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div>
                <label className="label">End Date</label>
                <input type="date" className="input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="label">Key Findings</label>
              <textarea className="input min-h-20 resize-none" rows={3}
                placeholder="Summarise the main results and conclusions…"
                value={findings} onChange={(e) => setFindings(e.target.value)} />
            </div>

            <div>
              <label className="label">Publication DOI <span className="text-gray-400">(optional)</span></label>
              <input className="input font-mono text-sm" placeholder="10.xxxx/xxxx"
                value={doi} onChange={(e) => setDoi(e.target.value)} />
            </div>

            <div className="flex items-center gap-3 py-2">
              <input type="checkbox" id="addOutcome" checked={showOutcome} onChange={(e) => setShowOutcome(e.target.checked)}
                className="w-4 h-4 accent-forest-600" />
              <label htmlFor="addOutcome" className="text-sm text-gray-700 cursor-pointer">
                Also log a patient outcome record for this trial
              </label>
            </div>

            {submitMut.isError && <PageError message="Failed to submit trial. Please try again." />}

            <button type="submit" className="btn-primary w-full py-3 flex items-center justify-center gap-2"
              disabled={submitMut.isPending || !herbId || !title}>
              {submitMut.isPending ? <><Spinner /> Submitting…</> : "Submit Trial →"}
            </button>
          </form>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-forest-50 border border-forest-300 text-forest-700 px-4 py-3 rounded-lg text-sm">
            ✅ Trial submitted! {showOutcome ? "Now log the patient outcome below." : ""}
          </div>

          {showOutcome && (
            <div className="card">
              <h2 className="section-title mb-4">Log Patient Outcome (anonymized)</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Age Group</label>
                    <select className="select" value={ageGroup} onChange={(e) => setAgeGroup(e.target.value as AgeGroup)}>
                      <option value="child">Child</option>
                      <option value="adult">Adult</option>
                      <option value="elderly">Elderly</option>
                    </select>
                  </div>
                  <div>
                    <label className="label">Sex</label>
                    <select className="select" value={sex} onChange={(e) => setSex(e.target.value as Sex)}>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="not_disclosed">Not Disclosed</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="label">Condition Treated <span className="text-red-500">*</span></label>
                  <input className="input" placeholder="e.g. Type 2 Diabetes"
                    value={condition} onChange={(e) => setCondition(e.target.value)} required />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Dosage Used</label>
                    <input className="input" placeholder="e.g. 500mg twice daily"
                      value={dosage} onChange={(e) => setDosage(e.target.value)} />
                  </div>
                  <div>
                    <label className="label">Duration (days)</label>
                    <input type="number" min="1" className="input" placeholder="e.g. 90"
                      value={duration} onChange={(e) => setDuration(e.target.value)} />
                  </div>
                </div>

                <div>
                  <label className="label">Outcome <span className="text-red-500">*</span></label>
                  <select className="select" value={outcome} onChange={(e) => setOutcome(e.target.value as OutcomeResult)}>
                    <option value="improved">Improved</option>
                    <option value="no_change">No Change</option>
                    <option value="worsened">Worsened</option>
                    <option value="adverse_reaction">Adverse Reaction</option>
                  </select>
                </div>

                {(outcome === "worsened" || outcome === "adverse_reaction") && (
                  <div>
                    <label className="label">Adverse Details</label>
                    <textarea className="input min-h-20 resize-none" rows={3}
                      placeholder="Describe the adverse event or worsened condition…"
                      value={adverseDetails} onChange={(e) => setAdverseDetails(e.target.value)} />
                  </div>
                )}

                {outcomeMut.isError && <PageError message="Failed to log outcome. Please try again." />}

                <button className="btn-primary w-full py-3 flex items-center justify-center gap-2"
                  onClick={handleLogOutcome}
                  disabled={outcomeMut.isPending || !condition}>
                  {outcomeMut.isPending ? <><Spinner /> Logging…</> : "Log Outcome & View Trial →"}
                </button>
              </div>
            </div>
          )}

          {!showOutcome && (
            <button className="btn-primary w-full py-3" onClick={() => navigate(`/research/trials/${trialId}`)}>
              View Trial →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
