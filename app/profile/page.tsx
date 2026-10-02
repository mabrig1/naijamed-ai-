"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type Profile = {
  name: string;
  dob: string;
  state: string;
  lga: string;
  email: string;
  nextOfKinName: string;
  nextOfKinPhone: string;
};

const empty: Profile = {
  name: "",
  dob: "",
  state: "",
  lga: "",
  email: "",
  nextOfKinName: "",
  nextOfKinPhone: ""
};

export default function ProfilePage() {
  const router = useRouter();
  const [form, setForm] = useState<Profile>(empty);
  const [message, setMessage] = useState("");
  const [deleteText, setDeleteText] = useState("");

  useEffect(() => {
    fetch("/api/profile", { cache: "no-store" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        setForm({
          name: data.name || "",
          dob: data.dob || "",
          state: data.state || "",
          lga: data.lga || "",
          email: data.email || "",
          nextOfKinName: data.next_of_kin?.name || "",
          nextOfKinPhone: data.next_of_kin?.phone || ""
        });
      });
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    const response = await fetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form)
    });
    const body = await response.json();
    setMessage(response.ok ? "Profile saved." : body.error || "Could not save profile");
  }

  async function deleteAccount() {
    if (deleteText !== "DELETE") return;
    const response = await fetch("/api/privacy/delete", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: deleteText })
    });
    if (response.ok) {
      router.replace("/");
      router.refresh();
      return;
    }
    const body = await response.json();
    setMessage(body.error || "Account deletion failed.");
  }

  const field = (key: keyof Profile, label: string, type = "text") => (
    <label className="block">
      <span className="text-sm font-semibold text-green-900">{label}</span>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="mt-2 h-12 w-full rounded-xl border bg-white px-4 outline-none focus:ring-2 focus:ring-green-600"
      />
    </label>
  );

  return (
    <main className="mx-auto min-h-screen max-w-xl px-5 py-6">
      <div className="flex items-center justify-between">
        <Brand />
        <Link href="/dashboard" className="text-sm font-semibold text-green-700">Dashboard</Link>
      </div>

      <Card className="mt-8">
        <h1 className="font-serif text-3xl font-semibold text-green-900">Your profile</h1>
        <form onSubmit={save} className="mt-6 grid gap-4">
          {field("name", "Full name")}
          {field("dob", "Date of birth", "date")}
          {field("state", "State")}
          {field("lga", "LGA")}
          {field("email", "Email (optional)", "email")}
          {field("nextOfKinName", "Next-of-kin name")}
          {field("nextOfKinPhone", "Next-of-kin phone", "tel")}
          <Button className="mt-2 w-full">Save profile</Button>
        </form>
        {message ? <p className="mt-4 rounded-xl bg-green-50 p-3 text-sm text-green-900">{message}</p> : null}
      </Card>

      <Card className="mt-5">
        <CardTitle>Your data rights</CardTitle>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Download a copy of your MediNaija data or permanently delete your account.
        </p>
        <Button asChild variant="outline" className="mt-4 w-full">
          <a href="/api/privacy/export">Download my data</a>
        </Button>

        <div className="mt-6 border-t pt-5">
          <label className="text-sm font-semibold text-red-800">Type DELETE to permanently remove your account</label>
          <input
            value={deleteText}
            onChange={(e) => setDeleteText(e.target.value)}
            className="mt-2 h-12 w-full rounded-xl border border-red-200 bg-white px-4 outline-none"
          />
          <button
            type="button"
            disabled={deleteText !== "DELETE"}
            onClick={deleteAccount}
            className="mt-3 min-h-12 w-full rounded-xl bg-red-700 px-4 font-semibold text-white disabled:opacity-40"
          >
            Delete my account
          </button>
        </div>
      </Card>
    </main>
  );
}
