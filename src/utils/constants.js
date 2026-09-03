export const RISK = {
  LOW: "LOW",
  MEDIUM: "MEDIUM",
  HIGH: "HIGH",
};

export const SEVERITY = {
  MILD: "MILD",
  MODERATE: "MODERATE",
  SEVERE: "SEVERE",
};

export const DURATION_OPTIONS = [
  { value: "JUST_STARTED", label: "Just started" },
  { value: "FEW_HOURS", label: "A few hours" },
  { value: "SINCE_YESTERDAY", label: "Since yesterday" },
  { value: "SEVERAL_DAYS", label: "Several days" },
];

export const FEELING_OPTIONS = [
  { value: "GREAT", label: "Great", emoji: "😊" },
  { value: "GOOD", label: "Good", emoji: "🙂" },
  { value: "OKAY", label: "Okay", emoji: "😐" },
  { value: "NOT_GOOD", label: "Not Good", emoji: "😟" },
  { value: "VERY_UNWELL", label: "Very Unwell", emoji: "😣" },
];

export const SYMPTOM_OPTIONS = [
  "Pain",
  "Fatigue",
  "Fever",
  "Dizziness",
  "Nausea",
  "Breathing Difficulty",
  "Chest Discomfort",
  "Other",
];

export const SEVERITY_OPTIONS = [
  { value: "MILD", label: "Mild" },
  { value: "MODERATE", label: "Moderate" },
  { value: "SEVERE", label: "Severe" },
];

export const ADHERENCE_OPTIONS = [
  { value: "ALL_TAKEN", label: "Yes, all of them" },
  { value: "MISSED_ONE_DOSE", label: "Missed one dose" },
  { value: "MISSED_MULTIPLE", label: "Missed multiple doses" },
];

export const MED_TIME_OF_DAY = {
  MORNING: "MORNING",
  AFTERNOON: "AFTERNOON",
  EVENING: "EVENING",
};

export const ALERT_STATUS = {
  ACTIVE: "ACTIVE",
  RESOLVED: "RESOLVED",
};
