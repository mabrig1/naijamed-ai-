import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { api } from "../../lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setLoading(true);
    setError("");
    try {
      await api.post("/api/auth/reset-password", { token, new_password: password });
      navigate("/login?reset=success");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Invalid or expired link. Please request a new one.");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-forest-800 to-forest-600 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8 text-center">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Invalid Reset Link</h2>
          <p className="text-gray-500 text-sm mb-4">This link is missing a token. Please request a new reset link.</p>
          <Link to="/forgot-password" className="text-forest-700 hover:underline text-sm">Request new link →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-forest-800 to-forest-600 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🔐</div>
          <h1 className="text-2xl font-bold text-forest-800">Set New Password</h1>
          <p className="text-sm text-gray-500 mt-1">Choose a strong password (min 8 characters)</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-700 text-sm">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
              placeholder="Min 8 characters"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
            <input
              type="password"
              required
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
              placeholder="Repeat password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-forest-700 text-white rounded-xl py-3 font-semibold text-sm hover:bg-forest-800 transition-colors disabled:opacity-50"
          >
            {loading ? "Saving…" : "Set New Password →"}
          </button>
          <div className="text-center">
            <Link to="/login" className="text-sm text-forest-700 hover:underline">← Back to Sign In</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
