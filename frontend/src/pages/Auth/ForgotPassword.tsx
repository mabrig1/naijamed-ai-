import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.post("/api/auth/forgot-password", { email });
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-forest-800 to-forest-600 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🌿</div>
          <h1 className="text-2xl font-bold text-forest-800">Reset Your Password</h1>
          <p className="text-sm text-gray-500 mt-1">
            Enter your email and we'll send a reset link
          </p>
        </div>

        {sent ? (
          <div className="text-center space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-green-800 text-sm">
              ✅ If that email exists in our system, a reset link has been sent. Check your inbox (and spam folder).
            </div>
            <Link to="/login" className="block text-sm text-forest-700 hover:underline">
              ← Back to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-700 text-sm">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
                placeholder="you@example.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-forest-700 text-white rounded-xl py-3 font-semibold text-sm hover:bg-forest-800 transition-colors disabled:opacity-50"
            >
              {loading ? "Sending…" : "Send Reset Link"}
            </button>
            <div className="text-center">
              <Link to="/login" className="text-sm text-forest-700 hover:underline">
                ← Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
