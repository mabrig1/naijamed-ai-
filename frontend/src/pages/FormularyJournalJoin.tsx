import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner } from "../components/Layout";

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Could not join this Journal Club room.";
}

export default function FormularyJournalJoin() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function join() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post<{ room_id: string }>("/api/formulary/journal/join", { token });
      navigate("/formulary/journal", { replace: true, state: { roomId: data.room_id } });
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl py-10">
      <section className="rounded-3xl bg-forest-900 p-7 text-white">
        <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Private Formulary invitation</div>
        <h1 className="mt-3 text-3xl font-bold">Join Journal Club Live Room</h1>
        <p className="mt-3 text-sm leading-6 text-forest-100">
          Joining shares your account name with room participants and gives you access to the room's structured paper evidence, appraisal notes and discussion record. It does not give you the host's uploaded PDF file.
        </p>
      </section>

      {error && <div className="mt-5"><PageError message={error} /></div>}

      <section className="card mt-6">
        <p className="text-sm leading-6 text-gray-600">
          Only continue if you recognize the person or group that sent this invitation. The host can lock or close the room at any time.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <button className="btn-primary flex items-center gap-2" disabled={loading || token.length < 16} onClick={join}>
            {loading && <Spinner />} Join room
          </button>
          <Link className="btn-outline" to="/formulary/journal">My Journal Clubs</Link>
        </div>
      </section>
    </div>
  );
}
