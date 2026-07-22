# Patient Management and Evidence Officer Update

## Changes
- Added Patient Management page with list, search, add, view, edit and safe delete.
- Patient data uses the existing `Patient` table.
- Linked forensic cases are displayed when viewing a patient.
- Evidence Officer (Field Officer) can open and view Cases and case details.
- Evidence Officer cannot add, edit or delete cases because those actions still require `Manage Cases`.

## Run
1. Copy your `.env` into `Code/backend/.env`.
2. Confirm the existing database contains `Patient`, `PatientHistory`, `ForensicCase`, RBAC tables and permissions.
3. Run `run_backend.bat` on Windows.
4. Open http://127.0.0.1:8000

## Important
Patient deletion is blocked when a forensic case is linked to the patient, protecting referential integrity.

## Court Reports visibility fix
- Added COURT_REPORTS to the Doctor navigation menu.
- Allowed the Doctor role to open the Court Reports client route.
- Automatically grants the Doctor role the Generate Court Reports permission during backend startup when missing.
