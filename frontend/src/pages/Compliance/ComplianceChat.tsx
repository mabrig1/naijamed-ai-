import { useState, useRef, useEffect } from "react";
import { useComplianceChat } from "../../hooks/useCompliance";
import { Spinner } from "../../components/Layout";
import type { ChatMessage } from "../../types";

const STARTER_QUESTIONS = [
  "What documents are required to register a herbal product with NAFDAC?",
  "How long does the NAFDAC approval process take?",
  "What is the fee schedule for product registration?",
  "What are the labeling requirements for herbal supplements?",
  "Can a traditional herb seller get a manufacturing license?",
];

export default function ComplianceChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hello! I'm your NAFDAC Compliance AI Assistant. I can help you understand Nigeria's regulatory requirements for herbal and pharmaceutical products. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState("");
  const chatMut = useComplianceChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(question?: string) {
    const text = question ?? input.trim();
    if (!text) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const res = await chatMut.mutateAsync({
      question: text,
      context: messages.map((m) => `${m.role}: ${m.content}`).join("\n"),
    });

    setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-5 rounded-xl flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🏛️</span>
          <div>
            <h1 className="text-xl font-bold">NAFDAC Compliance AI Assistant</h1>
            <p className="text-forest-200 text-xs mt-0.5">Powered by Claude · For guidance only — always consult a certified NAFDAC consultant</p>
          </div>
        </div>
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto space-y-3 px-1">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <span className="w-8 h-8 rounded-full bg-forest-600 text-white flex items-center justify-center text-sm shrink-0 mr-2 mt-0.5">
                🤖
              </span>
            )}
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-forest-600 text-white rounded-tr-none"
                  : "bg-white border border-gray-200 text-gray-700 rounded-tl-none shadow-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {chatMut.isPending && (
          <div className="flex justify-start">
            <span className="w-8 h-8 rounded-full bg-forest-600 text-white flex items-center justify-center text-sm shrink-0 mr-2">🤖</span>
            <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
              <Spinner />
              <span className="text-sm text-gray-500">Claude is thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Starter questions (show only at start) */}
      {messages.length <= 1 && (
        <div className="flex-shrink-0">
          <p className="text-xs text-gray-400 mb-2 px-1">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {STARTER_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="text-xs bg-forest-50 border border-forest-200 text-forest-700 px-3 py-1.5 rounded-full hover:bg-forest-100 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="flex-shrink-0 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg text-xs text-amber-700">
        ⚠️ This is AI guidance only. Always verify with NAFDAC directly or consult a certified regulatory consultant before making compliance decisions.
      </div>

      {/* Input */}
      <div className="flex-shrink-0 flex gap-3">
        <textarea
          className="input flex-1 resize-none min-h-12 max-h-28"
          rows={2}
          placeholder="Ask about NAFDAC requirements, fees, timelines, documentation… (Enter to send)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={chatMut.isPending}
        />
        <button
          className="btn-primary px-5 shrink-0 self-end"
          onClick={() => handleSend()}
          disabled={chatMut.isPending || !input.trim()}
        >
          {chatMut.isPending ? <Spinner /> : "Send"}
        </button>
      </div>
    </div>
  );
}
