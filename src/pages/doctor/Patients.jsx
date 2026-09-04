import React, { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Plus, Loader2 } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import Button from "../../components/ui/Button";
import PatientCard from "../../components/healthcare/PatientCard";
import RiskBadge from "../../components/healthcare/RiskBadge";
import EmptyState from "../../components/ui/EmptyState";
import { useData } from "../../context/DataContext";
import { formatRelativeTime } from "../../utils/dateUtils";
import { searchMyPatients } from "../../api/patients.api";
import { USE_MOCK } from "../../api/client";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "LOW", label: "Stable" },
  { key: "MEDIUM", label: "Medium Risk" },
  { key: "HIGH", label: "High Risk" },
];

export default function Patients() {
  const { patients: allPatients } = useData();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("ALL");
  // Debounced server-side search results (live mode only - see
  // api/patients.api.js::searchMyPatients). null means "not currently
  // searching", i.e. fall back to the doctor's already-loaded full list.
  const [liveResults, setLiveResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);

  useEffect(() => {
    if (USE_MOCK) return; // no backend to search - mock mode filters in-memory below
    const trimmed = query.trim();
    if (!trimmed) {
      setLiveResults(null);
      setSearchError(null);
      setSearchLoading(false);
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    const handle = setTimeout(async () => {
      try {
        const results = await searchMyPatients(trimmed);
        setLiveResults(results);
      } catch (err) {
        setSearchError(err.message || "Search failed. Please try again.");
        setLiveResults(null);
      } finally {
        setSearchLoading(false);
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [query]);

  const baseList = liveResults !== null ? liveResults : allPatients;

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return baseList.filter((p) => {
      const matchesFilter = filter === "ALL" || p.riskLevel === filter;
      // Live mode: liveResults already came back name/phone-filtered from
      // the backend, so re-filtering by the same free text here would be
      // redundant. Mock mode has no backend to hit, so it still needs the
      // in-memory filter.
      const matchesQuery =
        !USE_MOCK || !q
          ? true
          : (p.name || "").toLowerCase().includes(q) || (p.condition || "").toLowerCase().includes(q);
      return matchesFilter && matchesQuery;
    });
  }, [baseList, filter, query]);

  return (
    <>
      <Topbar title="Patients" subtitle="Manage and monitor your patients." />
      <main className="flex-1 px-6 py-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-xs">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search patients…"
              className="w-full rounded-xl border border-ink-300/30 bg-white py-2.5 pl-9 pr-9 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            {searchLoading && (
              <Loader2
                size={15}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-ink-300"
              />
            )}
          </div>
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate("/doctor/patients/new")}>
            Add Patient
          </Button>
        </div>

        <div className="mb-5 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                filter === f.key
                  ? "bg-brand-700 text-white"
                  : "border border-ink-300/25 bg-white text-ink-600 hover:bg-canvas-soft"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {searchError && (
          <div className="mb-5 rounded-xl border border-risk-high/30 bg-risk-high-bg px-4 py-3 text-sm text-risk-high">
            {searchError}
          </div>
        )}

        {filtered.length ? (
          <>
            <div className="hidden overflow-hidden rounded-2xl border border-ink-300/15 bg-white shadow-card lg:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-ink-300/15 text-xs uppercase tracking-wide text-ink-300">
                    <th className="px-5 py-3 font-medium">Patient</th>
                    <th className="px-5 py-3 font-medium">Latest Check-in</th>
                    <th className="px-5 py-3 font-medium">Risk</th>
                    <th className="px-5 py-3 font-medium">Adherence</th>
                    <th className="px-5 py-3 font-medium">Next Follow-up</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((p) => (
                    <tr key={p.id} className="border-b border-ink-300/10 last:border-0 hover:bg-canvas-soft/50">
                      <td className="px-5 py-3">
                        <p className="font-medium text-ink-900">{p.name}</p>
                        <p className="text-xs text-ink-500">{p.condition}</p>
                      </td>
                      <td className="px-5 py-3 text-ink-600">
                        {p.lastCheckIn ? formatRelativeTime(p.lastCheckIn) : "—"}
                      </td>
                      <td className="px-5 py-3">
                        <RiskBadge level={p.riskLevel} size="sm" />
                      </td>
                      <td className="px-5 py-3 text-ink-600">{p.medicationAdherencePct}%</td>
                      <td className="px-5 py-3 text-ink-600">
                        {p.nextFollowUp
                          ? new Date(p.nextFollowUp.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                          : "—"}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => navigate(`/doctor/patients/${p.id}`)}
                          className="text-sm font-medium text-brand-700 hover:underline"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid gap-3 lg:hidden">
              {filtered.map((p) => (
                <PatientCard key={p.id} patient={p} onClick={() => navigate(`/doctor/patients/${p.id}`)} />
              ))}
            </div>
          </>
        ) : (
          <EmptyState title="No patients match" description="Try a different search or filter." />
        )}
      </main>
    </>
  );
}
