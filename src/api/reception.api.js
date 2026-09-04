// DEAD FILE - intentionally emptied, not deleted (workspace files can't be
// removed from here without the user's say-so).
//
// This module predates the real receptionist integration and called a
// `/reception/patients` endpoint that never existed anywhere in the Django
// backend (no such route is registered in config/urls.py). It was never
// imported by any page - grep across src/ turns up zero usages - but a
// working, in-use module already covers this exact need:
//
//   src/api/receptionist.api.js
//     - searchPatients({ phone, name, dob })  -> GET  /patients/search/
//     - createReceptionistPatient(data)       -> POST /patients/
//     - getDoctorsList()                      -> GET  /auth/doctors/
//
// Use that module instead. This file is kept in place (rather than deleted)
// purely so it can't be silently re-created with the same broken contract;
// it exports nothing.
export {};
