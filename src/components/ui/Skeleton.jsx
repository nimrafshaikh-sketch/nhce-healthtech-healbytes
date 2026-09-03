import React from "react";

export default function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-ink-900/5 ${className}`} />;
}
