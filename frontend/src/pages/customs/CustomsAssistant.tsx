import { useState, useRef, useEffect } from "react";
import { useCustomsChat, useHSLookup } from "../../hooks/useCustoms";
import type { CustomsChatMessage } from "../../hooks/useCustoms";
import { Spinner } from "../../components/Layout";

const QUICK_ACTIONS = [
  { icon: "🔢", label: "HS Code for Moringa", message: "What is the HS code for Moringa powder?" },
  { icon: "🇩🇪", label: "Germany requirements", message: "What does Germany require to import Nigerian herbs?" },
  { icon: "📋", label: "Register with NEPC", message: "How do I register my herbal product export with NEPC?" },
  { icon: "📝", label: "Form-M procedure", message: "How does Form-M work for herb exports from Nigeria?" },
  { icon: "🇬🇧", label: "UK import rules", message: "What are the UK import requirements for dried Nigerian herbs?" },
  { icon: "💰", label: "Repatriate forex", message: "How do I repatriate export earnings via CBN? What is the timeline?" },
];

const HERB_LIST = [
  "Moringa","Bitter Leaf","Turmeric","Neem (Dogoyaro)","African Basil",
  "Ginger","Garlic","Hibiscus (Zobo)","African Pepper","Aloe Vera",
  "Tiger Nut","Baobab","Soursop Leaf","Shea Butter","Black Seed",
];

function HSCodePanel() {
  const [herbInput, setHerbInput] = useState("");
  const lookup = useHSLookup();

  async function handleLookup() {
    if (!herbInput.trim()) return;
    await lookup.mutateAsync(herbInput.trim());
  }

  return (
    <div className="card space-y-4">
      <h2 className="font-bold text-forest-700 flex items-center gap-2">
        <span>🔢</span> HS Code Lookup
      </h2>
      <p className="text-xs text-gray-500">
        Enter a herb name to get its harmonised system code for customs declarations.
      </p>

      <div className="space-y-2">
        <input
          className="input text-sm"
          placeholder="e.g. Moringa powder"
          value={herbInput}
          onChange={(e) => setHerbInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLookup()}
        />
        <div className="flex flex-wrap gap-1">
          {HERB_LIST.slice(0, 8).map((h) => (
            <button key={h} type="button"
              onClick={() => { setHerbInput(h); }}
              className="text-xs bg-forest-50 text-forest-700 px-2 py-0.5 rounded-full hover:bg-forest-100 transition-colors">
              {h}
            </button>
          ))}
        </div>
        <button onClick={handleLookup} disabled={!herbInput || lookup.isPending}
          className="btn-primary w-full text-sm">
          {lookup.isPending ? <Spinner /> : "Look Up HS Code →"}
        </button>
      </div>

      {lookup.data && (
        <div className="bg-forest-50 border border-forest-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">HS Code</span>
            <span className="font-bold text-forest-700 text-lg tracking-widest">
              {lookup.data.hs_code}
            </span>
          </div>
          <p className="text-sm text-gray-700">{lookup.data.description}</p>
          {lookup.data.duty_rate && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-500">Duty rate:</span>
              <span className="font-medium text-gray-700">{lookup.data.duty_rate}</span>
            </div>
          )}
          {lookup.data.required_permits.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Required permits:</p>
              <div className="flex flex-wrap gap-1">
                {lookup.data.required_permits.map((p) => (
                  <span key={p} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">{p}</span>
                ))}
              </div>
            </div>
          )}
          {lookup.data.notes && (
            <p className="text-xs text-gray-500 italic border-t border-forest-100 pt-2">
              {lookup.data.notes}
            </p>
          )}
        </div>
      )}

      {lookup.isError && (
        <p className="text-red-600 text-xs">⚠️ Could not find HS code. Try a more specific herb name.</p>
      )}
    </div>
  );
}

function ChatMessage({ msg }: { msg: CustomsChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
        isUser ? "bg-forest-600 text-white" : "bg-gold-100 text-gold-700 border border-gold-300"
      }`}>
        {isUser ? "U" : "🤖"}
      </div>

      <div className={`max-w-[75%] space-y-2 ${isUser ? "items-end" : ""} flex flex-col`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-forest-600 text-white rounded-tr-none"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm"
        }`}>
          {msg.content}
        </div>

        {/* Suggested follow-ups */}
        {!isUser && msg.suggested_questions && msg.suggested_questions.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.suggested_questions.map((q, i) => (
              <button key={i}
                className="text-xs bg-forest-50 border border-forest-200 text-forest-700 px-2.5 py-1 rounded-full hover:bg-forest-100 transition-colors text-left">
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function CustomsAssistant() {
  const [messages, setMessages] = useState<CustomsChatMessage[]>([
    {
      role: "assistant",
      content: "👋 Hello! I'm your NaijaMed Customs AI. I can help you with HS codes, country import requirements, NEPC/NAFDAC registration, Form-M procedures, forex repatriation, and more.\n\nWhat do you need help with today?",
      suggested_questions: [
        "What is the HS code for Moringa?",
        "How do I register with NEPC?",
        "What does Germany require?",
      ],
    },
  ]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const chatMut = useCustomsChat();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    const userMsg: CustomsChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await chatMut.mutateAsync({ message: text, history });
      const assistantMsg: CustomsChatMessage = {
        role: "assistant",
        content: response.answer,
        suggested_questions: response.suggested_questions,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: "⚠️ Sorry, I couldn't process your request. Please try again.",
      }]);
    }
  }

  function _handleSuggestedQuestion(q: string) { sendMessage(q); }

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-5 rounded-2xl">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <span>🛃</span> Customs AI Assistant
        </h1>
        <p className="text-forest-100 text-sm mt-1">
          AI-powered guidance on HS codes, country requirements, NEPC/NAFDAC, Form-M, and forex repatriation
        </p>
        <p className="text-forest-200 text-xs mt-2">
          ⚠️ Advisory only — always verify with a licensed customs agent for formal declarations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Chat — left 2/3 */}
        <div className="lg:col-span-2 flex flex-col">
          {/* Quick actions */}
          <div className="bg-white rounded-xl border border-gray-100 p-3 mb-3">
            <p className="text-xs font-medium text-gray-500 mb-2">Quick Actions</p>
            <div className="flex flex-wrap gap-2">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.label}
                  onClick={() => sendMessage(qa.message)}
                  disabled={chatMut.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-forest-50 hover:bg-forest-100 text-forest-700 text-xs font-medium rounded-full transition-colors disabled:opacity-50"
                >
                  <span>{qa.icon}</span>
                  <span>{qa.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 bg-gray-50 rounded-xl border border-gray-100 p-4 overflow-y-auto min-h-[420px] max-h-[520px] space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage key={i} msg={msg} />
            ))}

            {/* Typing indicator */}
            {chatMut.isPending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gold-100 border border-gold-300 flex items-center justify-center text-sm flex-shrink-0">
                  🤖
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-3">
                  <div className="flex gap-1 items-center h-4">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="mt-3 flex gap-2">
            <input
              className="input flex-1"
              placeholder="Ask about HS codes, country requirements, NEPC, customs..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              disabled={chatMut.isPending}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || chatMut.isPending}
              className="btn-primary px-5"
            >
              {chatMut.isPending ? <Spinner /> : "Send →"}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5">Press Enter to send · Shift+Enter for new line</p>
        </div>

        {/* HS Code panel — right sidebar */}
        <div className="space-y-4">
          <HSCodePanel />

          {/* Useful links */}
          <div className="card">
            <h3 className="font-bold text-forest-700 mb-3">🔗 Official Resources</h3>
            <div className="space-y-2">
              {[
                { label: "NAFDAC Official", url: "https://www.nafdac.gov.ng", icon: "🏥" },
                { label: "NEPC Nigeria", url: "https://www.nepc.gov.ng", icon: "📊" },
                { label: "Nigeria Customs", url: "https://customs.gov.ng", icon: "🛃" },
                { label: "CBN Forex Policy", url: "https://www.cbn.gov.ng", icon: "🏦" },
                { label: "NAQS Nigeria", url: "https://naqs.gov.ng", icon: "🌿" },
              ].map(({ label, url, icon }) => (
                <a key={label} href={url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-forest-700 transition-colors">
                  <span>{icon}</span>
                  <span className="hover:underline">{label}</span>
                  <span className="text-gray-300 ml-auto text-xs">↗</span>
                </a>
              ))}
            </div>
          </div>

          {/* Topic shortcuts */}
          <div className="card">
            <h3 className="font-bold text-forest-700 mb-3">📋 Topic Guides</h3>
            <div className="space-y-1.5">
              {[
                ["NEPC Registration", "Walk me through NEPC exporter registration step by step"],
                ["Form-M Explained", "Explain Form-M for Nigerian herb exports in simple terms"],
                ["CBN Repatriation", "What is the CBN forex repatriation requirement for exporters?"],
                ["Phytosanitary Certs", "How do I get a phytosanitary certificate for my herbs?"],
                ["EU Requirements", "What are EU import requirements for Nigerian herbal products?"],
              ].map(([label, msg]) => (
                <button key={label} onClick={() => sendMessage(msg as string)}
                  className="w-full text-left text-xs text-gray-600 hover:text-forest-700 hover:bg-forest-50 px-3 py-2 rounded-lg transition-colors flex items-center justify-between">
                  <span>{label}</span>
                  <span className="text-gray-300">→</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
