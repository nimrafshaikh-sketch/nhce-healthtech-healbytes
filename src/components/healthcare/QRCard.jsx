import React from "react";

function hashGrid(seed, size) {
  const cells = [];
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  for (let i = 0; i < size * size; i += 1) {
    h = (h * 1103515245 + 12345) >>> 0;
    cells.push(h % 5 === 0 || h % 7 === 0);
  }
  return cells;
}

export default function QRCard({ value = "healbytes", size = 11 }) {
  const cells = hashGrid(String(value), size);
  return (
    <div
      className="mx-auto grid w-56 gap-0.5 rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card"
      style={{ gridTemplateColumns: `repeat(${size}, 1fr)` }}
    >
      {cells.map((filled, i) => (
        <div key={i} className={`aspect-square rounded-[2px] ${filled ? "bg-ink-900" : "bg-transparent"}`} />
      ))}
    </div>
  );
}
