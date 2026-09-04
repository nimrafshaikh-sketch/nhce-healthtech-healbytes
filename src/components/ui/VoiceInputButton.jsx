import React, { useState, useEffect, useRef, useCallback } from "react";
import { Mic, MicOff } from "lucide-react";

export default function VoiceInputButton({
  onTranscript,
  disabled = false,
  themeColor = "brand", // "brand" (emerald/teal) or "indigo" (receptionist)
  className = "",
}) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  // Use a ref for the callback so the SpeechRecognition instance never gets recreated
  const onTranscriptRef = useRef(onTranscript);

  // Keep the ref in sync with the latest prop
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false; // Only fire with final results
      recognition.lang = "en-US";
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
        isListeningRef.current = true;
        setErrorMsg(null);
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            transcript += event.results[i][0].transcript;
          }
        }
        if (transcript && onTranscriptRef.current) {
          onTranscriptRef.current(transcript.trim());
        }
      };

      recognition.onerror = (event) => {
        if (
          event.error === "not-allowed" ||
          event.error === "service-not-allowed"
        ) {
          setErrorMsg("Microphone access denied. Please allow microphone access in your browser settings.");
          isListeningRef.current = false;
          setIsListening(false);
        } else if (event.error === "no-speech") {
          // No speech detected — silently restart if still listening
          // (handled by onend)
        } else if (event.error === "aborted") {
          // User stopped — do nothing
          isListeningRef.current = false;
          setIsListening(false);
        } else {
          setErrorMsg(`Voice error: ${event.error}`);
          isListeningRef.current = false;
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        // If user hasn't clicked stop, restart to keep listening
        if (isListeningRef.current) {
          try {
            recognition.start();
          } catch {
            // If restart fails, stop cleanly
            isListeningRef.current = false;
            setIsListening(false);
          }
        } else {
          setIsListening(false);
        }
      };

      recognitionRef.current = recognition;
    } catch (err) {
      console.warn("SpeechRecognition init error:", err);
      setIsSupported(false);
    }

    return () => {
      isListeningRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, []); // No dependencies — only create once

  const toggleListening = useCallback(
    (e) => {
      e.preventDefault();
      if (disabled || !isSupported || !recognitionRef.current) return;

      if (isListeningRef.current) {
        // STOP
        isListeningRef.current = false;
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
        setIsListening(false);
      } else {
        // START
        setErrorMsg(null);
        isListeningRef.current = true;
        try {
          recognitionRef.current.start();
        } catch (err) {
          console.warn("SpeechRecognition start error:", err);
          // If already running, abort and retry
          try {
            recognitionRef.current.abort();
            setTimeout(() => {
              if (recognitionRef.current && isListeningRef.current) {
                try {
                  recognitionRef.current.start();
                } catch {
                  isListeningRef.current = false;
                  setIsListening(false);
                }
              }
            }, 150);
          } catch {
            isListeningRef.current = false;
            setIsListening(false);
          }
        }
      }
    },
    [disabled, isSupported]
  );

  const isBrand = themeColor === "brand";

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        title="Speech recognition is not supported in this browser"
        className={`flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed opacity-60 dark:border-slate-700 dark:bg-slate-800 ${className}`}
      >
        <MicOff className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        title={
          isListening
            ? "Stop listening"
            : errorMsg || "Click to speak (Voice Input)"
        }
        className={`relative flex h-10 w-10 items-center justify-center rounded-xl border transition-all shrink-0 ${
          isListening
            ? "border-rose-400 bg-rose-500 text-white shadow-md shadow-rose-500/30 animate-pulse"
            : isBrand
            ? "border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:bg-brand-50 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-brand-500 dark:hover:bg-slate-700"
            : "border-slate-300 bg-white text-slate-700 hover:border-indigo-500 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-indigo-500 dark:hover:bg-slate-700"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} ${className}`}
      >
        {isListening ? (
          <>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-600"></span>
            </span>
            <Mic className="h-4 w-4 text-white" />
          </>
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>

      {/* Floating live recording indicator tooltip */}
      {isListening && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-900/90 px-2.5 py-1 text-[11px] font-medium text-white shadow-md backdrop-blur-xs pointer-events-none flex items-center gap-1.5 z-20">
          <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
          Listening... speak now
        </div>
      )}
    </div>
  );
}
