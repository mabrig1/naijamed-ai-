import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/axios";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "researcher" });

  const mutation = useMutation({
    mutationFn: async () => { await api.post("/api/auth/register", form); },
    onSuccess: () => navigate("/login"),
  });

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl font-bold text-brand-800 mb-1">Create your account</h1>
        <p className="text-gray-500 text-sm mb-6">Join the NigerFlora BioSciences community</p>
        <form onSubmit={(e: FormEvent) => { e.preventDefault(); mutation.mutate(); }} className="space-y-4">
          <div>
            <label className="label" htmlFor="full_name">Full Name</label>
            <input id="full_name" type="text" className="input" value={form.full_name} onChange={set("full_name")} required />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="input" value={form.email} onChange={set("email")} required />
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input id="password" type="password" className="input" value={form.password} onChange={set("password")} required minLength={8} />
          </div>
          <div>
            <label className="label" htmlFor="role">Role</label>
            <select id="role" className="input" value={form.role} onChange={set("role")}>
              <option value="researcher">Researcher</option>
              <option value="herbalist">Herbalist</option>
              <option value="producer">Producer</option>
            </select>
          </div>
          {mutation.isError && <p className="text-red-600 text-sm">Registration failed. Please try again.</p>}
          <button type="submit" disabled={mutation.isPending} className="btn-primary w-full">
            {mutation.isPending ? "Creating account…" : "Create Account"}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-600 hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
