import React from "react";

const PALETTE = [
  "bg-brand-100 text-brand-800",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-800",
  "bg-stone-200 text-ink-700",
  "bg-emerald-100 text-emerald-800",
];

function hashToIndex(str = "", mod) {
  let h = 0;
  for (let i = 0; i < str.length; i += 1) h = (h * 31 + str.charCodeAt(i)) % 1000;
  return h % mod;
}

export default function Avatar({ name = "", initials, size = "md" }) {
  const sizes = { sm: "h-8 w-8 text-xs", md: "h-10 w-10 text-sm", lg: "h-14 w-14 text-base" };
  const label =
    initials ||
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0])
      .join("")
      .toUpperCase();
  const tone = PALETTE[hashToIndex(name, PALETTE.length)];
  return (
    <div className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${sizes[size]} ${tone}`}>
      {label}
    </div>
  );
}
