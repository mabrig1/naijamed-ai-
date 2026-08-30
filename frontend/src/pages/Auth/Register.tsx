import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Spinner } from "../../components/Layout";

const ROLES = [
  { value: "researcher", label: "🧬 Researcher", desc: "M.Sc., Ph.D., academic and discovery services" },
  { value: "patient", label: "👤 Individual", desc: "Personal health navigation and triage" },
  { value: "doctor", label: "🩺 Doctor", desc: "Verified clinical workspace and consultations" },
  { value: "clinic", label: "🏥 Clinic", desc: "Provider workspace and team-based care" },
  { value: "hmo", label: "🛡️ HMO / Partner", desc: "Enterprise health and integration workflows" },
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "researcher" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field: string) {
    return (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((value) => ({ ...value, [field]: event.target.value }));
  }

  function passwordStrength(password: string): { label: string; color: string; pct: number } {
    if (!password) return { label: "", color: "bg-gray-200", pct: 0 };
    if (password.length < 8) return { label: "Weak", color: "bg-red-400", pct: 30 };
    const mixed = /[0-9]/.test(password) && /[a-zA-Z]/.test(password);
    if (mixed && password.length >= 10) return { label: "Strong", color: "bg-forest-500", pct: 100 };
    return { label: mixed ? "Good" : "Add a number", color: "bg-gold-400", pct: mixed ? 75 : 50 };
  }

  const strength = passwordStrength(form.password);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (form.password.length < 8 || !/[0-9]/.test(form.password) || !/[a-zA-Z]/.test(form.password)) {
      setError("Password must be at least 8 characters and contain a letter and a number.");
      return;
    }
    setLoading(true);
    try {
      await register(form.email, form.full_name, form.password, form.role);
      navigate(form.role === "researcher" ? "/research-studio" : "/dashboard");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string | { msg: string }[] } } })?.response?.data?.detail;
      if (Array.isArray(detail)) setError(detail[0]?.msg ?? "Registration failed.");
      else setError(detail ?? "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-hero-pattern px-4 py-10">
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-8 text-center">
          <div className="mb-3 text-5xl">🌿</div>
          <h1 className="text-3xl font-bold text-white">Join NigerFlora BioSciences</h1>
          <p className="mt-1 text-forest-200">Choose the workspace that matches what you want to achieve.</p>
        </div>

        <div className="card shadow-2xl">
          <h2 className="text-2xl font-bold text-forest-800">Create your account</h2>
          <p className="mt-1 text-sm text-gray-500">Research services, health workflows and provider tools use one secure account.</p>

          {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">⚠️ {error}</div>}

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {ROLES.map((role) => (
              <button
                key={role.value}
                type="button"
                onClick={() => setForm((value) => ({ ...value, role: role.value }))}
                className={`rounded-xl border-2 p-3 text-left text-sm transition-all ${
                  form.role === role.value
                    ? "border-forest-600 bg-forest-50 text-forest-800"
                    : "border-gray-200 text-gray-600 hover:border-forest-300"
                }`}
              >
                <div className="font-semibold">{role.label}</div>
                <div className="mt-1 text-xs leading-5 opacity-75">{role.desc}</div>
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="mt-7 grid gap-5 md:grid-cols-2">
            <div>
              <label className="label">Full name</label>
              <input className="input" value={form.full_name} onChange={set("full_name")} placeholder="Adaeze Okafor" required autoComplete="name" />
            </div>
            <div>
              <label className="label">Email address</label>
              <input className="input" type="email" value={form.email} onChange={set("email")} placeholder="you@example.com" required autoComplete="email" />
            </div>
            <div className="md:col-span-2">
              <label className="label">Password</label>
              <input className="input" type="password" value={form.password} onChange={set("password")} placeholder="Minimum 8 characters + one number" required autoComplete="new-password" />
              {form.password && (
                <div className="mt-2">
                  <div className="h-1.5 w-full rounded-full bg-gray-200">
                    <div className={`${strength.color} h-1.5 rounded-full transition-all`} style={{ width: `${strength.pct}%` }} />
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{strength.label}</div>
                </div>
              )}
            </div>
            <div className="md:col-span-2">
              <button type="submit" className="btn-primary flex w-full items-center justify-center gap-2" disabled={loading}>
                {loading ? <><Spinner /> Creating account…</> : "Create account →"}
              </button>
            </div>
          </form>

          <div className="mt-6 border-t border-gray-100 pt-5 text-center text-sm text-gray-500">
            Already have an account? <Link to="/login" className="font-semibold text-forest-600 hover:underline">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
