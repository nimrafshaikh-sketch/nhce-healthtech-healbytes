import React from "react";

const COLOR = { LOW: "#2D9166", MEDIUM: "#B5760B", HIGH: "#B23A2E" };

export default function RiskScore({ score = 0, level = "LOW", size = 72 }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(Math.max(score, 0), 100) / 100) * circumference;
  const color = COLOR[level] || COLOR.LOW;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={radius} strokeWidth="6" fill="none" stroke="rgba(28,29,27,0.06)" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth="6"
          fill="none"
          stroke={color}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 700ms ease-out" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-lg font-bold leading-none" style={{ color }}>
          {score}
        </span>
        <span className="text-[10px] text-ink-500">/100</span>
      </div>
    </div>
  );
}
