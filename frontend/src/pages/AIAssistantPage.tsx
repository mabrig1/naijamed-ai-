import { useState, FormEvent, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/axios";

type Provider = "gemini" | "claude";

interface Message {
  role: "user" | "assistant";
  content: string;
  provider?: Provider;
}

export default function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [provider, setProvider] = useState<Provider>("gemini");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const mutation = useMutation({
    mutationFn: async (prompt: string) => {
      const { data } = await api.post<{ response: string }>("/api/ai/ask", { prompt, provider });
      return data.response;
    },
    onSuccess: (response) => {
      setMessages((prev) => [...prev, { role: "assistant", content: response, provider }]);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    mutation.mutate(input);
    setInput("");
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-brand-800">AI Research Assistant</h1>
        <div className="flex gap-2">
          {(["gemini", "claude"] as Provider[]).map((p) => (
            <button key={p} onClick={() => setProvider(p)}
              className={`px-3 py-1 text-sm rounded-full font-medium transition-colors ${provider === p ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {p === "gemini" ? "🔵 Gemini" : "🟣 Claude"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-12">
            Ask anything about Nigerian herbal medicine, phytochemistry, or pharmaceutical formulation.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-brand-600 text-white rounded-br-none"
                : "bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm"
            }`}>
              {msg.role === "assistant" && msg.provider && (
                <p className="text-xs text-gray-400 mb-1">{msg.provider === "gemini" ? "🔵 Gemini" : "🟣 Claude"}</p>
              )}
              {msg.content}
            </div>
          </div>
        ))}
        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
              <span className="text-gray-400 text-sm animate-pulse">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input type="text" className="input flex-1"
          placeholder="Ask about herbs, phytochemistry, formulations…"
          value={input} onChange={(e) => setInput(e.target.value)} disabled={mutation.isPending} />
        <button type="submit" disabled={mutation.isPending || !input.trim()} className="btn-primary px-5">
          Send
        </button>
      </form>
    </div>
  );
}
