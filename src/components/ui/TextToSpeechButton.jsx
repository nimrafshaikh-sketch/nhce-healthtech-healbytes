import React, { useState, useEffect } from "react";
import { Volume2, Square } from "lucide-react";

/**
 * Clean markdown symbols for smooth, natural text-to-speech pronunciation.
 */
function cleanTextForSpeech(rawText) {
  if (!rawText) return "";
  return rawText
    .replace(/[*_~`#>]/g, "") // remove markdown bold, italics, code, headers
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // convert markdown links [text](url) to plain text
    .replace(/[-*•]\s+/g, ", ") // convert bullet points to natural speech pauses
    .replace(/\s+/g, " ") // clean excessive whitespace
    .trim();
}

export default function TextToSpeechButton({
  text,
  themeColor = "brand", // "brand" or "indigo"
  className = "",
}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setIsSupported(false);
    }
  }, []);

  // Sync state if speech completes or global cancel occurs
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    const handleEndOrCancel = () => {
      if (window.speechSynthesis && !window.speechSynthesis.speaking) {
        setIsSpeaking(false);
      }
    };

    const interval = setInterval(handleEndOrCancel, 300);
    return () => {
      clearInterval(interval);
      if (isSpeaking && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isSpeaking]);

  const handleToggleSpeak = () => {
    if (!isSupported || typeof window === "undefined") return;

    const synth = window.speechSynthesis;
    if (!synth) return;

    if (isSpeaking) {
      synth.cancel();
      setIsSpeaking(false);
      return;
    }

    // Cancel any previous active speech across the app
    synth.cancel();

    const cleanContent = cleanTextForSpeech(text);
    if (!cleanContent) return;

    const utterance = new SpeechSynthesisUtterance(cleanContent);
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
    utterance.lang = "en-US";

    // Pick the best available natural-sounding English voice
    const voices = synth.getVoices();
    if (voices.length > 0) {
      // Preferred voices in priority order (macOS premium, Google, Microsoft)
      const preferred = [
        "Samantha",        // macOS - natural female
        "Karen",           // macOS - natural female (Australian)
        "Daniel",          // macOS - natural male (British)
        "Google US English",
        "Google UK English Female",
        "Google UK English Male",
        "Microsoft Zira",  // Windows - clear female
        "Microsoft David", // Windows - clear male
        "Fiona",           // macOS
        "Moira",           // macOS
        "Tessa",           // macOS
        "Alex",            // macOS
      ];

      let bestVoice = null;

      // 1. Try exact preferred name match
      for (const name of preferred) {
        const found = voices.find((v) => v.name.includes(name));
        if (found) {
          bestVoice = found;
          break;
        }
      }

      // 2. Fallback: any English voice marked as "premium" or "enhanced"
      if (!bestVoice) {
        bestVoice = voices.find(
          (v) =>
            v.lang.startsWith("en") &&
            (v.name.toLowerCase().includes("premium") ||
             v.name.toLowerCase().includes("enhanced") ||
             v.name.toLowerCase().includes("natural"))
        );
      }

      // 3. Fallback: any English voice from Google or Microsoft
      if (!bestVoice) {
        bestVoice = voices.find(
          (v) =>
            v.lang.startsWith("en") &&
            (v.name.includes("Google") || v.name.includes("Microsoft"))
        );
      }

      // 4. Fallback: any en-US or en-GB voice
      if (!bestVoice) {
        bestVoice = voices.find(
          (v) => v.lang === "en-US" || v.lang === "en-GB"
        );
      }

      if (bestVoice) {
        utterance.voice = bestVoice;
        utterance.lang = bestVoice.lang;
      }
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = (e) => {
      if (e.error !== "interrupted" && e.error !== "canceled") {
        console.warn("Speech synthesis error:", e);
      }
      setIsSpeaking(false);
    };

    synth.speak(utterance);
  };

  if (!isSupported) {
    return null;
  }

  const isBrand = themeColor === "brand";

  return (
    <button
      type="button"
      onClick={handleToggleSpeak}
      title={isSpeaking ? "Stop reading response aloud" : "Listen to this AI response (Text-to-Speech)"}
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all border shrink-0 cursor-pointer ${
        isSpeaking
          ? "border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 dark:border-rose-800 dark:bg-rose-950/60 dark:text-rose-300 animate-pulse"
          : isBrand
          ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:border-emerald-300 hover:bg-emerald-100/80 dark:border-emerald-800/40 dark:bg-emerald-950/40 dark:text-emerald-300"
          : "border-indigo-200 bg-indigo-50 text-indigo-800 hover:border-indigo-300 hover:bg-indigo-100/80 dark:border-indigo-800/40 dark:bg-indigo-950/40 dark:text-indigo-300"
      } ${className}`}
    >
      {isSpeaking ? (
        <>
          <Square className="h-3 w-3 fill-current" />
          <span>Stop</span>
        </>
      ) : (
        <>
          <Volume2 className="h-3.5 w-3.5" />
          <span>Listen</span>
        </>
      )}
    </button>
  );
}
