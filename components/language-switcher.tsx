"use client";

import { useState } from "react";

const languages = [
  ["en", "English"],
  ["yo", "Yorùbá"],
  ["ha", "Hausa"],
  ["ig", "Igbo"],
  ["pcm", "Pidgin"]
] as const;

export function LanguageSwitcher() {
  const [value, setValue] = useState("en");

  async function change(language: string) {
    setValue(language);
    await fetch("/api/profile/language", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language })
    });
  }

  return (
    <label className="text-xs font-semibold text-slate-500">
      Language
      <select
        value={value}
        onChange={(e) => change(e.target.value)}
        className="ml-2 rounded-lg border bg-white px-2 py-2 text-sm text-green-900"
      >
        {languages.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
      </select>
    </label>
  );
}
