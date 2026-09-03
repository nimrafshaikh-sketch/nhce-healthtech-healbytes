// TEMPORARY FRONTEND DEMO LOGIC ONLY.
// This entire file simulates what POST /ai/analyze-checkin will return.
// Replace by pointing api/ai.api.js at the real endpoint — no UI changes needed.

const HIGH_TRIGGER_SYMPTOMS = ["Chest Discomfort", "Breathing Difficulty"];

function joinNames(names) {
  if (names.length === 0) return "";
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

export function analyzeCheckin(payload) {
  const symptoms = payload.symptoms || [];
  const overallFeeling = payload.overallFeeling;
  const medicationAdherence = payload.medicationAdherence;

  const symptomNames = symptoms.map((s) => s.name);
  const hasSevere = symptoms.some((s) => s.severity === "SEVERE");
  const hasModerate = symptoms.some((s) => s.severity === "MODERATE");
  const hasHighTrigger = symptoms.some((s) => HIGH_TRIGGER_SYMPTOMS.includes(s.name));
  const isVeryUnwell = overallFeeling === "VERY_UNWELL";
  const missedMultiple = medicationAdherence === "MISSED_MULTIPLE";

  if (hasSevere || hasHighTrigger || isVeryUnwell) {
    return {
      riskLevel: "HIGH",
      riskScore: 87,
      reason: symptomNames.length
        ? `${joinNames(symptomNames)} reported since your last check-in, with symptoms trending toward more severe. This pattern warrants prompt review.`
        : "Your overall feeling has dropped sharply compared with recent check-ins.",
      alertRecipient: ["DOCTOR", "CARETAKER"],
      followUpAction: "Contact patient within 2 hours.",
      recommendation: "Seek guidance from your healthcare provider.",
    };
  }

  if (hasModerate || missedMultiple) {
    return {
      riskLevel: "MEDIUM",
      riskScore: 62,
      reason: missedMultiple
        ? "Multiple missed medication doses were reported, which can affect recovery if it continues."
        : `${joinNames(symptomNames)} reported at moderate severity — a change worth monitoring closely.`,
      alertRecipient: ["DOCTOR"],
      followUpAction: "Review at next scheduled check-in; contact patient if symptoms persist.",
      recommendation: "Continue monitoring your symptoms and complete tomorrow's check-in.",
    };
  }

  return {
    riskLevel: "LOW",
    riskScore: 18,
    reason: "Your responses are consistent with a stable recovery and do not indicate an immediate concern.",
    alertRecipient: [],
    followUpAction: "No action required — continue routine monitoring.",
    recommendation: "Keep up with your medication schedule and daily check-ins.",
  };
}
