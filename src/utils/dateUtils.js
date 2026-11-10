export function minutesAgo(n) {
  return new Date(Date.now() - n * 60 * 1000);
}

export function hoursAgo(n) {
  return new Date(Date.now() - n * 60 * 60 * 1000);
}

export function daysAgo(n) {
  return new Date(Date.now() - n * 24 * 60 * 60 * 1000);
}

export function isDateOnlyString(input) {
  return typeof input === "string" && /^\d{4}-\d{2}-\d{2}$/.test(input.trim());
}

export function parseDateInput(input) {
  if (!input) return null;
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input;
  }
  if (isDateOnlyString(input)) {
    const [y, m, d] = input.trim().split("-").map(Number);
    const local = new Date(y, m - 1, d);
    return Number.isNaN(local.getTime()) ? null : local;
  }
  const parsed = new Date(input);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function isSameLocalDay(a, b = new Date()) {
  const da = parseDateInput(a);
  const db = parseDateInput(b);
  if (!da || !db) return false;
  return da.toDateString() === db.toDateString();
}

export function formatRelativeTime(input) {
  const date = parseDateInput(input);
  if (!date) return "—";
  if (isDateOnlyString(input)) {
    return formatDayLabel(input);
  }
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.round(diffMs / 60000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? "" : "s"} ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hour${diffHr === 1 ? "" : "s"} ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay === 1) return "Yesterday";
  if (diffDay < 7) return `${diffDay} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatTime(input) {
  if (isDateOnlyString(input)) return "";
  const date = parseDateInput(input);
  if (!date) return "";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatDateTime(input) {
  const date = parseDateInput(input);
  if (!date) return "—";
  if (isDateOnlyString(input)) return formatDayLabel(input);
  return `${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}, ${formatTime(date)}`;
}

export function formatDayLabel(input) {
  const date = parseDateInput(input);
  if (!date) return "—";
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString(undefined, { month: "long", day: "numeric" });
}
