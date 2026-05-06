import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Spinner } from "../../components/Layout";

const ROLES = [
  { value: "farmer",        label: "🌾 Farmer",        desc: "List herbs and track market demand" },
  { value: "researcher",    label: "🔬 Researcher",     desc: "Submit clinical trials and log outcomes" },
  { value: "pharma_company",label: "🏭 Pharma Company", desc: "Browse herbs, generate formulations, file NAFDAC docs" },
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "researcher" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field: string) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  function passwordStrength(p: string): { label: string; color: string; pct: number } {
    if (p.length === 0) return { label: "", color: "bg-gray-200", pct: 0 };
    if (p.length < 6)   return { label: "Weak",   color: "bg-red-400",  pct: 25 };
    if (p.length < 8)   return { label: "Fair",   color: "bg-gold-400", pct: 50 };
    const strong = /[0-9]/.test(p) && /[a-zA-Z]/.test(p);
    if (strong && p.length >= 10) return { label: "Strong",  color: "bg-forest-500", pct: 100 };
    return { label: "Good", color: "bg-forest-400", pct: 75 };
  }

  const strength = passwordStrength(form.password);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (!/[0-9]/.test(form.password)) { setError("Password must contain at least one number."); return; }
    setLoading(true);
    try {
      await register(form.email, form.full_name, form.password, form.role);
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string | { msg: string }[] } } })?.response?.data?.detail;
      if (Array.isArray(msg)) setError(msg[0]?.msg ?? "Registration failed.");
      else setError(msg ?? "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-hero-pattern flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🌿</div>
          <h1 className="text-3xl font-bold text-white">Join NaijaMed AI</h1>
          <p className="text-forest-200 mt-1">Create your free account today</p>
        </div>

        <div className="card shadow-2xl">
          <h2 className="text-2xl font-bold text-forest-700 mb-1">Create Account</h2>
          <p className="text-gray-500 text-sm mb-6">Choose your role to get a tailored experience</p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex gap-2">
              <span>⚠️</span> {error}
            </div>
          )}

          {/* Role selector */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            {ROLES.map((r) => (
              <button
                key={r.value}
                type="button"
                onClick={() => setForm((f) => ({ ...f, role: r.value }))}
                className={`p-3 rounded-xl border-2 text-left transition-all text-sm ${
                  form.role === r.value
                    ? "border-forest-600 bg-forest-50 text-forest-700"
                    : "border-gray-200 hover:border-forest-300 text-gray-500"
                }`}
              >
                <div className="font-semibold mb-0.5">{r.label}</div>
                <div className="text-xs leading-snug opacity-70">{r.desc}</div>
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="label">Full Name</label>
              <input type="text" className="input" placeholder="Adaeze Okafor" value={form.full_name}
                onChange={set("full_name")} required autoComplete="name" />
            </div>
            <div>
              <label className="label">Email address</label>
              <input type="email" className="input" placeholder="you@example.com" value={form.email}
                onChange={set("email")} required autoComplete="email" />
            </div>
            <div>
              <label className="label">Password</label>
              <input type="password" className="input" placeholder="Min 8 chars + one number" value={form.password}
                onChange={set("password")} required autoComplete="new-password" />
              {form.password && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div className={`${strength.color} h-1.5 rounded-full transition-all`} style={{ width: `${strength.pct}%` }} />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{strength.label}</div>
                </div>
              )}
            </div>

            <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={loading}>
              {loading ? <><Spinner /> Creating account…</> : "Create Account →"}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-gray-100 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link to="/login" className="text-forest-600 font-semibold hover:underline">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
