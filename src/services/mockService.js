import { generateId, generateInvitationCode } from "../utils/id";

export function getInitials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export function createPatientRecord(formData) {
  return {
    id: generateId("pat"),
    role: "PATIENT",
    name: formData.name,
    age: Number(formData.age) || null,
    gender: formData.gender,
    phone: formData.phone,
    email: formData.email,
    condition: formData.condition,
    diagnosis: formData.diagnosis,
    allergies: formData.allergies || "None known",
    notes: formData.notes || "",
    avatarInitials: getInitials(formData.name),
    caretaker: formData.caretaker,
    riskLevel: "LOW",
    riskScore: 0,
    reason: "No check-ins submitted yet.",
    followUpAction: "Awaiting first check-in.",
    recommendation: "",
    lastCheckIn: null,
    medicationAdherencePct: 100,
    invitationCode: generateInvitationCode(),
    joinedAt: new Date(),
    nextFollowUp: null,
  };
}
