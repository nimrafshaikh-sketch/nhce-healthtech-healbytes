import React, { useState, useRef, useEffect } from "react";
import { Sparkles, Send, Bot, User, Wrench, AlertCircle, RefreshCw, CheckCircle2, Calendar, UserCheck } from "lucide-react";
import { queryReceptionistAgent } from "../../api/ai.api";
import VoiceInputButton from "../ui/VoiceInputButton";
import TextToSpeechButton from "../ui/TextToSpeechButton";

const RECEPTION_QUICK_PROMPTS = [
  "Add patient Zynab Mathiya DOB 21 08 2005",
  "What appointments are scheduled for today?",
  "Show available doctors & their specializations",
  "Find patient with phone number 9876543210",
  "Check scheduled follow-ups for Rahul Verma",
];

export default function ReceptionistAgentChat({ onAppointmentCreated }) {
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

  const handleSend = async (textToSend) => {
    const question = textToSend || input;
    if (!question || !question.trim() || loading) return;

    setError(null);
    setInput("");

    const newHistory = [...messages, { role: "user", text: question.trim() }];
    setMessages(newHistory);
    setLoading(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role === "agent" ? "agent" : "user",
        text: m.text,
      }));

      const res = await queryReceptionistAgent({
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
        },
      ]);

      // If an appointment was scheduled/updated or a new patient was registered, trigger parent refresh
      if (
        res.tool_calls &&
        res.tool_calls.some(
          (tc) =>
            tc.tool_name === "schedule_appointment" ||
            tc.tool_name === "update_appointment_status" ||
            tc.tool_name === "register_patient"
        )
      ) {
        if (onAppointmentCreated) {
          onAppointmentCreated();
        }
      }
    } catch (err) {
      setError(err.message || "Failed to reach Receptionist AI Assistant. Please try again.");
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="flex flex-col rounded-2xl border border-indigo-200 bg-white/95 shadow-lg backdrop-blur-sm dark:border-indigo-800/40 dark:bg-slate-900/90 overflow-hidden transition-all">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-indigo-100 bg-gradient-to-r from-indigo-700 via-sky-700 to-teal-700 px-5 py-4 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/20 shadow-inner backdrop-blur-md">
            <Sparkles className="h-5 w-5 text-amber-200 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold tracking-tight text-white">Front-Desk AI Assistant</h3>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/20 px-2 py-0.5 text-xs font-semibold text-emerald-100 border border-emerald-300/30">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-ping" />
                Gemini Receptionist Agent Live
              </span>
            </div>
            <p className="text-xs text-white/80">
              Autonomous appointment booking, patient registry search, &amp; doctor schedule coordination
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
      <div className="flex-1 min-h-[260px] max-h-[440px] overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400 mb-3 shadow-sm border border-indigo-100 dark:border-indigo-800/30">
              <Calendar className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Reception &amp; Front-Desk Coordination AI
            </h4>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-md">
              Ask any front-desk question in plain English. The agent searches patient registries, checks doctor rosters, and books or manages appointments directly.
            </p>

            {/* Quick Prompt Pills */}
            <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-lg">
              {RECEPTION_QUICK_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSend(prompt)}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:bg-slate-700/60 shadow-xs"
                >
                  ✨ {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "agent" && (
              <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-sky-600 text-white shadow-sm">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "border border-slate-200 bg-slate-50/80 text-slate-800 shadow-sm dark:border-slate-700/60 dark:bg-slate-800/80 dark:text-slate-100"
              }`}
            >
              {/* Top Bar inside Agent Message: Actions + TextToSpeech */}
              {msg.role === "agent" && (
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200/60 dark:border-slate-700/60">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {msg.toolCalls && msg.toolCalls.length > 0 ? (
                      <>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                          <Wrench className="h-3 w-3" /> Actions:
                        </span>
                        {msg.toolCalls.map((tc, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-0.5 text-[11px] font-mono font-medium text-indigo-700 shadow-xs border border-indigo-200 dark:bg-slate-900 dark:text-indigo-300 dark:border-indigo-800"
                          >
                            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                            {tc.tool_name}
                          </span>
                        ))}
                      </>
                    ) : (
                      <span className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400">
                        Front-Desk Assistant
                      </span>
                    )}
                  </div>

                  {/* Text-to-Speech Listen Button */}
                  <TextToSpeechButton text={msg.text} themeColor="indigo" />
                </div>
              )}

              {/* Message text with markdown format */}
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
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <Bot className="h-4 w-4 animate-bounce" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-indigo-600 animate-ping" />
              Gemini is coordinating clinic records &amp; executing front-desk tools...
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
          placeholder="Ask anything, e.g. 'Add patient Zynab Mathiya DOB 21 08 2005' or 'What appointments are today?'..."
          disabled={loading}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        <VoiceInputButton
          onTranscript={(spokenText) => {
            setInput((prev) => (prev ? `${prev} ${spokenText}` : spokenText));
          }}
          disabled={loading}
          themeColor="indigo"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-sm shrink-0"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
