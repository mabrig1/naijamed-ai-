import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/axios";

interface Herb {
  id: number;
  common_name: string;
  scientific_name: string;
  local_names: string[];
  uses: string[];
  region: string;
}

export default function HerbsPage() {
  const [search, setSearch] = useState("");

  const { data, isLoading, isError } = useQuery<Herb[]>({
    queryKey: ["herbs", search],
    queryFn: async () => {
      const { data } = await api.get("/api/herbs", { params: { search } });
      return data;
    },
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-brand-800 mb-2">Herb Library</h1>
      <p className="text-gray-500 mb-6">Nigerian medicinal plants — documented and AI-classified</p>

      <input type="search" className="input max-w-sm mb-8" placeholder="Search herbs…"
        value={search} onChange={(e) => setSearch(e.target.value)} />

      {isLoading && <p className="text-gray-400">Loading herbs…</p>}
      {isError && <p className="text-red-500">Failed to load herbs.</p>}
      {data?.length === 0 && <p className="text-gray-400">No herbs found.</p>}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data?.map((herb) => (
          <div key={herb.id} className="card hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-brand-800">{herb.common_name}</h3>
                <p className="text-xs text-gray-400 italic">{herb.scientific_name}</p>
              </div>
              <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full">{herb.region}</span>
            </div>
            {herb.local_names.length > 0 && (
              <p className="text-xs text-gray-500 mb-3">Local: {herb.local_names.join(", ")}</p>
            )}
            <div className="flex flex-wrap gap-1">
              {herb.uses.map((use) => (
                <span key={use} className="text-xs bg-earth-100 text-earth-800 px-2 py-0.5 rounded-full">{use}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
