import React from "react";
import Button from "./Button";

export default function ErrorState({ message = "We couldn't load this information.", onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-ink-300/25 bg-white px-6 py-12 text-center">
      <p className="text-sm text-ink-700">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );
}
