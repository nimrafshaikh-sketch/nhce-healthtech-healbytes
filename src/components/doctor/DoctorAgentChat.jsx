import React, { useState, useRef, useEffect } from "react";
import { Sparkles, Send, Bot, User, Wrench, AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import { queryDoctorAgent } from "../../api/ai.api";
import VoiceInputButton from "../ui/VoiceInputButton";
import TextToSpeechButton from "../ui/TextToSpeechButton";

const QUICK_PROMPTS = [
  "What active medications is this patient taking?",
  "Summarize acute risks & latest check-in",
  "Show longitudinal history & symptom trends",
  "What follow-ups or clinical actions are needed?",
];

export default function DoctorAgentChat({ patientId: fixedPatientId, patientName: fixedPatientName, patients = [] }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Helper to resolve which patient is referenced in the natural language query
  const findReferencedPatient = (queryText) => {
    if (!queryText) return null;
    const lower = queryText.toLowerCase().trim();

    // 1. Direct ID check like "patient 39" or "#39"
    for (const p of patients) {
      if (lower.includes(`patient ${p.id}`) || lower.includes(`#${p.id}`) || lower.includes(`patient #${p.id}`)) {
        return p;
      }
    }

    // 2. Full name check
    for (const p of patients) {
      const pName = (p.name || p.full_name || "").toLowerCase().trim();
      if (pName && lower.includes(pName)) {
        return p;
      }
    }

    // 3. First name / Last name check
    for (const p of patients) {
      const pName = (p.name || p.full_name || "").toLowerCase().trim();
      const parts = pName.split(/\s+/).filter(Boolean);
      for (const part of parts) {
        if (part.length >= 3 && new RegExp(`\\b${part}\\b`, "i").test(lower)) {
          return p;
        }
      }
    }

    return null;
  };

  const handleSend = async (textToSend) => {
    const question = textToSend || input;
    if (!question || !question.trim() || loading) return;

    setError(null);
    setInput("");

    // Determine target patient
    const referencedPatient = findReferencedPatient(question);
    const targetPatientId = referencedPatient?.id || fixedPatientId || (patients.length > 0 ? patients[0].id : null);
    const targetPatientName = referencedPatient?.name || fixedPatientName || (targetPatientId ? `Patient #${targetPatientId}` : null);

    if (!targetPatientId) {
      setError("Please specify a patient name in your query (e.g., 'What medications is Rahul Verma taking?')");
      return;
    }

    const userEntry = {
      role: "user",
      text: question.trim(),
      patientName: targetPatientName,
      patientId: targetPatientId,
    };

    const newHistory = [...messages, userEntry];
    setMessages(newHistory);
    setLoading(true);

    try {
      // Build conversation history for multi-turn reasoning
      const historyPayload = messages.map((m) => ({
        role: m.role === "agent" ? "agent" : "user",
        text: m.text,
      }));

      const res = await queryDoctorAgent({
        patientId: targetPatientId,
        message: question.trim(),
        conversationHistory: historyPayload,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: res.reply,
          toolCalls: res.tool_calls || [],
          modelVersion: res.model_version,
          patientName: targetPatientName,
        },
      ]);
    } catch (err) {
      setError(err.message || "Failed to reach AI Doctor Copilot. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col rounded-2xl border border-brand-200 bg-white/95 shadow-lg backdrop-blur-sm dark:border-brand-800/40 dark:bg-slate-900/90 overflow-hidden transition-all">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-brand-100 bg-gradient-to-r from-brand-600 via-indigo-600 to-purple-600 px-5 py-4 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/20 shadow-inner backdrop-blur-md">
            <Sparkles className="h-5 w-5 text-amber-200 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold tracking-tight text-white">AI Clinical Copilot</h3>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/20 px-2 py-0.5 text-xs font-semibold text-emerald-100 border border-emerald-300/30">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-ping" />
                Gemini Agent Live
              </span>
            </div>
            <p className="text-xs text-white/80">
              Autonomous clinical reasoning across patient records &amp; diagnostics
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            setMessages([]);
            setError(null);
          }}
          title="Clear Chat"
          className="rounded-lg p-1.5 text-white/80 hover:bg-white/10 hover:text-white transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Messages Container */}
      <div className="flex-1 min-h-[280px] max-h-[460px] overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-400 mb-3 shadow-sm border border-brand-100 dark:border-brand-800/30">
              <Bot className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Ask any clinical question in plain English
            </h4>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-sm">
              The Doctor Agent automatically executes backend database tools to answer your questions with zero hallucinations.
            </p>

            {/* Quick Prompt Pills */}
            <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-lg">
              {(() => {
                const p1 = fixedPatientName || (patients[0]?.name || "Rahul Verma");
                const p2 = patients[1]?.name || "Eleanor Vance";
                const pills = fixedPatientName
                  ? [
                      `What active medications is ${p1} taking?`,
                      `Summarize acute risks & latest check-in for ${p1}`,
                      `Show longitudinal history & symptom trends for ${p1}`,
                      `What follow-ups or clinical actions are needed?`,
                    ]
                  : [
                      `What active medications is ${p1} taking?`,
                      `Summarize acute risks & latest check-in for ${p1}`,
                      `Show history and symptom trends for ${p2}`,
                      `What follow-ups are needed for ${p1}?`,
                    ];
                return pills.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-brand-400 hover:bg-brand-50 hover:text-brand-700 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-brand-500 dark:hover:bg-slate-700/60 shadow-xs"
                  >
                    ✨ {prompt}
                  </button>
                ));
              })()}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "agent" && (
              <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white shadow-sm">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-brand-600 text-white shadow-sm"
                  : "border border-slate-200 bg-slate-50/80 text-slate-800 shadow-sm dark:border-slate-700/60 dark:bg-slate-800/80 dark:text-slate-100"
              }`}
            >
              {/* Top Bar inside Agent Message: Patient/Tools + TextToSpeech */}
              {msg.role === "agent" && (
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200/60 dark:border-slate-700/60">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {msg.patientName && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700 border border-brand-200 dark:bg-brand-950 dark:text-brand-300 dark:border-brand-800">
                        👤 {msg.patientName}
                      </span>
                    )}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1 ml-1">
                          <Wrench className="h-3 w-3" /> Tools:
                        </span>
                        {msg.toolCalls.map((tc, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-0.5 text-[11px] font-mono font-medium text-brand-700 shadow-xs border border-brand-200 dark:bg-slate-900 dark:text-brand-300 dark:border-brand-800"
                          >
                            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                            {tc.tool_name}
                          </span>
                        ))}
                      </>
                    )}
                  </div>

                  {/* Text-to-Speech Listen Button */}
                  <TextToSpeechButton text={msg.text} themeColor="brand" />
                </div>
              )}

              {/* User Patient Badge */}
              {msg.role === "user" && msg.patientName && (
                <div className="mb-1.5">
                  <span className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold bg-white/20 text-white">
                    👤 {msg.patientName}
                  </span>
                </div>
              )}

              {/* Message text with basic markdown format */}
              <div className="whitespace-pre-line leading-relaxed">{msg.text}</div>
            </div>

            {msg.role === "user" && (
              <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
              <Bot className="h-4 w-4 animate-bounce" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-brand-600 animate-ping" />
              Gemini is analyzing patient records & executing tools...
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl bg-rose-50 p-3 text-xs text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/40">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-2 border-t border-slate-200/80 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/50"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything, e.g. 'What medications is Rahul Verma taking?' or 'Summarize risks for Eleanor Vance'..."
          disabled={loading}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        <VoiceInputButton
          onTranscript={(spokenText) => {
            setInput((prev) => (prev ? `${prev} ${spokenText}` : spokenText));
          }}
          disabled={loading}
          themeColor="brand"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-all shadow-sm shrink-0"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
