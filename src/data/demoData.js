import { hoursAgo, daysAgo, minutesAgo } from "../utils/dateUtils";

export const demoDoctor = {
  id: "doc_1",
  role: "DOCTOR",
  name: "Dr. Sarah Chen",
  specialty: "Internal Medicine",
  email: "sarah.chen@healbytes.demo",
  avatarInitials: "SC",
};

// id, condition, diagnosis snapshot used across the app
export const initialPatients = [
  {
    id: "pat_rahul",
    role: "PATIENT",
    name: "Rahul Sharma",
    age: 45,
    gender: "Male",
    phone: "+91 98450 11223",
    email: "rahul.sharma@healbytes.demo",
    condition: "Post-operative care",
    diagnosis: "Coronary artery bypass graft (CABG), 9 days post-op",
    allergies: "Penicillin",
    notes: "Lives with spouse. History of hypertension.",
    avatarInitials: "RS",
    caretaker: { name: "Anita Sharma", relationship: "Spouse", phone: "+91 98450 11224" },
    riskLevel: "HIGH",
    riskScore: 87,
    reason: "Chest discomfort and fatigue have increased over the last two check-ins.",
    followUpAction: "Contact patient within 2 hours.",
    recommendation: "Seek guidance from your healthcare provider.",
    lastCheckIn: minutesAgo(10),
    medicationAdherencePct: 78,
    invitationCode: "HB-7K29X",
    joinedAt: daysAgo(9),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-1), reason: "Post-op cardiac review" },
  },
  {
    id: "pat_priya",
    role: "PATIENT",
    name: "Priya Nair",
    age: 52,
    gender: "Female",
    phone: "+91 98450 22334",
    email: "priya.nair@healbytes.demo",
    condition: "Type 2 diabetes management",
    diagnosis: "Type 2 diabetes mellitus, recent insulin adjustment",
    allergies: "None known",
    notes: "Works night shifts; adherence affected by irregular schedule.",
    avatarInitials: "PN",
    caretaker: { name: "Rajesh Nair", relationship: "Husband", phone: "+91 98450 22335" },
    riskLevel: "MEDIUM",
    riskScore: 62,
    reason: "Medication adherence dropped below 60% this week.",
    followUpAction: "Review at next scheduled check-in; contact patient if pattern continues.",
    recommendation: "Continue monitoring your symptoms and complete tomorrow's check-in.",
    lastCheckIn: hoursAgo(3),
    medicationAdherencePct: 58,
    invitationCode: "HB-3M81Q",
    joinedAt: daysAgo(14),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-3), reason: "Insulin dosage review" },
  },
  {
    id: "pat_arjun",
    role: "PATIENT",
    name: "Arjun Mehta",
    age: 34,
    gender: "Male",
    phone: "+91 98450 33445",
    email: "arjun.mehta@healbytes.demo",
    condition: "Post-surgical recovery",
    diagnosis: "Laparoscopic appendectomy, 5 days post-op",
    allergies: "None known",
    notes: "Consistent daily check-ins, stable recovery.",
    avatarInitials: "AM",
    caretaker: { name: "Kavya Mehta", relationship: "Sister", phone: "+91 98450 33446" },
    riskLevel: "LOW",
    riskScore: 18,
    reason: "Responses are consistent with a stable recovery.",
    followUpAction: "No action required — continue routine monitoring.",
    recommendation: "Keep up with your medication schedule and daily check-ins.",
    lastCheckIn: hoursAgo(14),
    medicationAdherencePct: 96,
    invitationCode: "HB-9D45L",
    joinedAt: daysAgo(6),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-6), reason: "Wound check" },
  },
  {
    id: "pat_meera",
    role: "PATIENT",
    name: "Meera Iyer",
    age: 61,
    gender: "Female",
    phone: "+91 98450 44556",
    email: "meera.iyer@healbytes.demo",
    condition: "Hypertension management",
    diagnosis: "Stage 1 hypertension, on ACE inhibitor",
    allergies: "Sulfa drugs",
    notes: "Retired teacher. Very consistent with routine.",
    avatarInitials: "MI",
    caretaker: { name: "Suresh Iyer", relationship: "Husband", phone: "+91 98450 44557" },
    riskLevel: "LOW",
    riskScore: 22,
    reason: "Blood pressure readings and symptoms remain stable.",
    followUpAction: "No action required — continue routine monitoring.",
    recommendation: "Keep up with your medication schedule and daily check-ins.",
    lastCheckIn: hoursAgo(20),
    medicationAdherencePct: 100,
    invitationCode: "HB-2P67R",
    joinedAt: daysAgo(21),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-9), reason: "Routine BP review" },
  },
  {
    id: "pat_vikram",
    role: "PATIENT",
    name: "Vikram Singh",
    age: 58,
    gender: "Male",
    phone: "+91 98450 55667",
    email: "vikram.singh@healbytes.demo",
    condition: "COPD follow-up",
    diagnosis: "Chronic obstructive pulmonary disease, moderate",
    allergies: "None known",
    notes: "History of breathlessness on exertion.",
    avatarInitials: "VS",
    caretaker: { name: "Harpreet Singh", relationship: "Son", phone: "+91 98450 55668" },
    riskLevel: "MEDIUM",
    riskScore: 62,
    reason: "Fatigue reported at moderate severity across recent check-ins.",
    followUpAction: "Review at next scheduled check-in; contact patient if symptoms persist.",
    recommendation: "Continue monitoring your symptoms and complete tomorrow's check-in.",
    lastCheckIn: hoursAgo(6),
    medicationAdherencePct: 84,
    invitationCode: "HB-6T12W",
    joinedAt: daysAgo(11),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-2), reason: "Pulmonary function review" },
  },
  {
    id: "pat_ananya",
    role: "PATIENT",
    name: "Ananya Reddy",
    age: 29,
    gender: "Female",
    phone: "+91 98450 66778",
    email: "ananya.reddy@healbytes.demo",
    condition: "Post-partum recovery",
    diagnosis: "Uncomplicated vaginal delivery, 3 weeks post-partum",
    allergies: "None known",
    notes: "First child. Support from extended family at home.",
    avatarInitials: "AR",
    caretaker: { name: "Karthik Reddy", relationship: "Husband", phone: "+91 98450 66779" },
    riskLevel: "LOW",
    riskScore: 15,
    reason: "Recovery is progressing normally with no concerning symptoms.",
    followUpAction: "No action required — continue routine monitoring.",
    recommendation: "Keep up with your medication schedule and daily check-ins.",
    lastCheckIn: daysAgo(1),
    medicationAdherencePct: 92,
    invitationCode: "HB-5H93N",
    joinedAt: daysAgo(20),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-4), reason: "6-week postnatal check" },
  },
  {
    id: "pat_suresh",
    role: "PATIENT",
    name: "Suresh Kumar",
    age: 67,
    gender: "Male",
    phone: "+91 98450 77889",
    email: "suresh.kumar@healbytes.demo",
    condition: "Chronic kidney disease",
    diagnosis: "CKD stage 3, on dietary and medication management",
    allergies: "Ibuprofen",
    notes: "Caretaker reports occasional confusion about dosage timing.",
    avatarInitials: "SK",
    caretaker: { name: "Lakshmi Kumar", relationship: "Daughter", phone: "+91 98450 77890" },
    riskLevel: "HIGH",
    riskScore: 79,
    reason: "Multiple missed medication doses combined with reported swelling.",
    followUpAction: "Contact patient within 2 hours.",
    recommendation: "Seek guidance from your healthcare provider.",
    lastCheckIn: hoursAgo(1),
    medicationAdherencePct: 61,
    invitationCode: "HB-8B24F",
    joinedAt: daysAgo(30),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(0), reason: "Renal function review" },
  },
  {
    id: "pat_divya",
    role: "PATIENT",
    name: "Divya Menon",
    age: 41,
    gender: "Female",
    phone: "+91 98450 88990",
    email: "divya.menon@healbytes.demo",
    condition: "Thyroid management",
    diagnosis: "Hypothyroidism, on levothyroxine",
    allergies: "None known",
    notes: "Stable for the past two months.",
    avatarInitials: "DM",
    caretaker: { name: "Anil Menon", relationship: "Husband", phone: "+91 98450 88991" },
    riskLevel: "LOW",
    riskScore: 20,
    reason: "Thyroid symptoms remain well controlled.",
    followUpAction: "No action required — continue routine monitoring.",
    recommendation: "Keep up with your medication schedule and daily check-ins.",
    lastCheckIn: daysAgo(2),
    medicationAdherencePct: 98,
    invitationCode: "HB-4Y56J",
    joinedAt: daysAgo(45),
    nextFollowUp: { doctorName: "Dr. Sarah Chen", date: daysAgo(-14), reason: "Thyroid panel review" },
  },
];

export const initialMedications = [
  { id: "med_1", patientId: "pat_rahul", name: "Aspirin", dosage: "75 mg", timeOfDay: "MORNING", instructions: "After breakfast", frequency: "Once daily", status: "TAKEN", takenAt: hoursAgo(6) },
  { id: "med_2", patientId: "pat_rahul", name: "Atorvastatin", dosage: "20 mg", timeOfDay: "EVENING", instructions: "After dinner", frequency: "Once daily", status: "PENDING" },
  { id: "med_3", patientId: "pat_rahul", name: "Metoprolol", dosage: "25 mg", timeOfDay: "MORNING", instructions: "Before breakfast", frequency: "Twice daily", status: "MISSED" },

  { id: "med_4", patientId: "pat_priya", name: "Metformin", dosage: "500 mg", timeOfDay: "MORNING", instructions: "After breakfast", frequency: "Twice daily", status: "TAKEN", takenAt: hoursAgo(5) },
  { id: "med_5", patientId: "pat_priya", name: "Insulin Glargine", dosage: "10 units", timeOfDay: "EVENING", instructions: "Before bed", frequency: "Once daily", status: "PENDING" },

  { id: "med_6", patientId: "pat_arjun", name: "Paracetamol", dosage: "500 mg", timeOfDay: "AFTERNOON", instructions: "If needed for pain", frequency: "As needed", status: "TAKEN", takenAt: hoursAgo(3) },
  { id: "med_7", patientId: "pat_arjun", name: "Vitamin D", dosage: "1000 IU", timeOfDay: "EVENING", instructions: "After dinner", frequency: "Once daily", status: "PENDING" },

  { id: "med_8", patientId: "pat_meera", name: "Ramipril", dosage: "5 mg", timeOfDay: "MORNING", instructions: "Before breakfast", frequency: "Once daily", status: "TAKEN", takenAt: hoursAgo(9) },

  { id: "med_9", patientId: "pat_vikram", name: "Salbutamol Inhaler", dosage: "2 puffs", timeOfDay: "MORNING", instructions: "As needed for breathlessness", frequency: "Twice daily", status: "TAKEN", takenAt: hoursAgo(7) },
  { id: "med_10", patientId: "pat_vikram", name: "Tiotropium", dosage: "18 mcg", timeOfDay: "EVENING", instructions: "Before bed", frequency: "Once daily", status: "PENDING" },

  { id: "med_11", patientId: "pat_ananya", name: "Iron Supplement", dosage: "60 mg", timeOfDay: "MORNING", instructions: "After breakfast", frequency: "Once daily", status: "TAKEN", takenAt: hoursAgo(10) },

  { id: "med_12", patientId: "pat_suresh", name: "Furosemide", dosage: "40 mg", timeOfDay: "MORNING", instructions: "Before breakfast", frequency: "Once daily", status: "MISSED" },
  { id: "med_13", patientId: "pat_suresh", name: "Calcium Acetate", dosage: "667 mg", timeOfDay: "AFTERNOON", instructions: "With lunch", frequency: "Three times daily", status: "MISSED" },

  { id: "med_14", patientId: "pat_divya", name: "Levothyroxine", dosage: "50 mcg", timeOfDay: "MORNING", instructions: "On empty stomach", frequency: "Once daily", status: "TAKEN", takenAt: hoursAgo(11) },
];

export const initialCheckins = [
  { id: "chk_1", patientId: "pat_rahul", date: daysAgo(1), overallFeeling: "NOT_GOOD", symptoms: [{ name: "Chest Discomfort", severity: "MODERATE" }, { name: "Fatigue", severity: "MODERATE" }], duration: "SINCE_YESTERDAY", medicationAdherence: "MISSED_ONE_DOSE", notes: "", riskLevel: "MEDIUM", riskScore: 62 },
  { id: "chk_2", patientId: "pat_rahul", date: minutesAgo(10), overallFeeling: "NOT_GOOD", symptoms: [{ name: "Chest Discomfort", severity: "SEVERE" }, { name: "Fatigue", severity: "MODERATE" }], duration: "SINCE_YESTERDAY", medicationAdherence: "MISSED_ONE_DOSE", notes: "Feeling more tired today.", riskLevel: "HIGH", riskScore: 87 },

  { id: "chk_3", patientId: "pat_priya", date: daysAgo(2), overallFeeling: "OKAY", symptoms: [{ name: "Fatigue", severity: "MILD" }], duration: "FEW_HOURS", medicationAdherence: "MISSED_MULTIPLE", notes: "", riskLevel: "MEDIUM", riskScore: 62 },
  { id: "chk_4", patientId: "pat_priya", date: hoursAgo(3), overallFeeling: "OKAY", symptoms: [], duration: "JUST_STARTED", medicationAdherence: "MISSED_MULTIPLE", notes: "", riskLevel: "MEDIUM", riskScore: 62 },

  { id: "chk_5", patientId: "pat_arjun", date: daysAgo(2), overallFeeling: "GOOD", symptoms: [], duration: "JUST_STARTED", medicationAdherence: "ALL_TAKEN", notes: "", riskLevel: "LOW", riskScore: 18 },
  { id: "chk_6", patientId: "pat_arjun", date: hoursAgo(14), overallFeeling: "GREAT", symptoms: [], duration: "JUST_STARTED", medicationAdherence: "ALL_TAKEN", notes: "", riskLevel: "LOW", riskScore: 18 },

  { id: "chk_7", patientId: "pat_vikram", date: daysAgo(1), overallFeeling: "OKAY", symptoms: [{ name: "Fatigue", severity: "MODERATE" }], duration: "SEVERAL_DAYS", medicationAdherence: "ALL_TAKEN", notes: "", riskLevel: "MEDIUM", riskScore: 62 },
  { id: "chk_8", patientId: "pat_vikram", date: hoursAgo(6), overallFeeling: "OKAY", symptoms: [{ name: "Fatigue", severity: "MODERATE" }], duration: "SEVERAL_DAYS", medicationAdherence: "ALL_TAKEN", notes: "", riskLevel: "MEDIUM", riskScore: 62 },

  { id: "chk_9", patientId: "pat_suresh", date: daysAgo(1), overallFeeling: "NOT_GOOD", symptoms: [{ name: "Pain", severity: "MODERATE" }], duration: "SEVERAL_DAYS", medicationAdherence: "MISSED_MULTIPLE", notes: "", riskLevel: "MEDIUM", riskScore: 62 },
  { id: "chk_10", patientId: "pat_suresh", date: hoursAgo(1), overallFeeling: "NOT_GOOD", symptoms: [{ name: "Pain", severity: "SEVERE" }], duration: "SEVERAL_DAYS", medicationAdherence: "MISSED_MULTIPLE", notes: "Ankles feel swollen.", riskLevel: "HIGH", riskScore: 79 },
];

export const initialAlerts = [
  { id: "alert_1", patientId: "pat_rahul", patientName: "Rahul Sharma", avatarInitials: "RS", riskLevel: "HIGH", riskScore: 87, message: "Chest discomfort severity increased from Moderate to Severe.", detectedAt: minutesAgo(10), status: "ACTIVE" },
  { id: "alert_2", patientId: "pat_suresh", patientName: "Suresh Kumar", avatarInitials: "SK", riskLevel: "HIGH", riskScore: 79, message: "Multiple missed doses reported alongside worsening swelling.", detectedAt: hoursAgo(1), status: "ACTIVE" },
  { id: "alert_3", patientId: "pat_priya", patientName: "Priya Nair", avatarInitials: "PN", riskLevel: "MEDIUM", riskScore: 62, message: "Medication adherence dropped below 60% this week.", detectedAt: hoursAgo(3), status: "ACTIVE" },
  { id: "alert_4", patientId: "pat_vikram", patientName: "Vikram Singh", avatarInitials: "VS", riskLevel: "MEDIUM", riskScore: 62, message: "Fatigue pattern reported across two consecutive check-ins.", detectedAt: hoursAgo(6), status: "ACTIVE" },
  { id: "alert_5", patientId: "pat_arjun", patientName: "Arjun Mehta", avatarInitials: "AM", riskLevel: "LOW", riskScore: 24, message: "Mild soreness at incision site, resolved after review.", detectedAt: daysAgo(3), status: "RESOLVED" },
];

export const demoReceptionist = {
  id: "rec_1",
  role: "RECEPTIONIST",
  name: "Anita Desai",
  email: "reception@healbytes.demo",
  avatarInitials: "AD",
};

export const demoLabTech = {
  id: "lab_1",
  role: "LAB_TECH",
  name: "Vikram Tech",
  email: "lab@healbytes.demo",
  avatarInitials: "VT",
};

export const initialPrescriptions = [
  {
    id: "presc_1",
    patientId: "pat_rahul",
    doctorId: "doc_1",
    date: daysAgo(1),
    medications: [
      { name: "Aspirin", dosage: "75 mg", frequency: "Once daily", duration: "30 days", instructions: "After breakfast" },
      { name: "Atorvastatin", dosage: "20 mg", frequency: "Once daily", duration: "30 days", instructions: "After dinner" }
    ],
    status: "ACTIVE"
  }
];

export const initialLabRequests = [
  {
    id: "req_1",
    patientId: "pat_priya",
    patientName: "Priya Nair",
    doctorId: "doc_1",
    doctorName: "Dr. Sarah Chen",
    testType: "HbA1c",
    status: "REQUESTED",
    createdAt: hoursAgo(2),
    expectedBy: "Today, 5:00 PM"
  },
  {
    id: "req_2",
    patientId: "pat_rahul",
    patientName: "Rahul Sharma",
    doctorId: "doc_1",
    doctorName: "Dr. Sarah Chen",
    testType: "CBC",
    status: "IN_PROGRESS",
    createdAt: hoursAgo(5),
    expectedBy: "Today, 2:00 PM"
  }
];

export const initialLabResults = [
  {
    id: "res_1",
    patientId: "pat_meera",
    doctorId: "doc_1",
    testType: "Lipid Panel",
    status: "COMPLETED",
    releaseStatus: "RELEASED",
    date: daysAgo(3),
    values: [
      { name: "Total Cholesterol", value: "190", unit: "mg/dL", referenceRange: "< 200", flag: "NORMAL" },
      { name: "LDL", value: "110", unit: "mg/dL", referenceRange: "< 100", flag: "HIGH" },
      { name: "HDL", value: "55", unit: "mg/dL", referenceRange: "> 50", flag: "NORMAL" }
    ],
    aiAnalysis: "Cholesterol levels are borderline. Suggest continued monitoring and dietary management."
  }
];

export const initialDocuments = [
  {
    id: "doc_1",
    patientId: "pat_rahul",
    documentType: "DISCHARGE_SUMMARY",
    uploadedBy: "Dr. Sarah Chen",
    date: daysAgo(9),
    fileName: "discharge_summary_rahul.pdf",
    status: "PROCESSED"
  }
];

export const initialAppointments = [
  {
    id: "appt_1",
    patientId: "pat_priya",
    doctorId: "doc_1",
    doctorName: "Dr. Sarah Chen",
    date: daysAgo(-3),
    time: "10:30 AM",
    reason: "Insulin dosage review",
    status: "CONFIRMED"
  }
];
