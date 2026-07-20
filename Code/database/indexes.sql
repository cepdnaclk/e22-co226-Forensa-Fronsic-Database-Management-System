-- ==========================================
-- INDEXES FOR ForensicMedicalDB
-- ==========================================

USE ForensicMedicalDB;

-- ==========================================
-- INDEXES FOR Patient Table
-- ==========================================
CREATE INDEX idx_patient_name ON Patient(FullName);
CREATE INDEX idx_patient_nic ON Patient(NIC);
CREATE INDEX idx_patient_registration_date ON Patient(RegistrationDate);

-- ==========================================
-- INDEXES FOR ForensicCase Table
-- ==========================================
CREATE INDEX idx_case_patient ON ForensicCase(PatientID);
CREATE INDEX idx_case_type ON ForensicCase(CaseType);
CREATE INDEX idx_case_status ON ForensicCase(Status);
CREATE INDEX idx_case_incident_date ON ForensicCase(IncidentDate);

-- ==========================================
-- INDEXES FOR Incident Table
-- ==========================================
CREATE INDEX idx_incident_case ON Incident(CaseID);
CREATE INDEX idx_incident_type ON Incident(IncidentType);

-- ==========================================
-- INDEXES FOR Staff Table
-- ==========================================
CREATE INDEX idx_staff_name ON Staff(StaffName);
CREATE INDEX idx_staff_role ON Staff(Role);

-- ==========================================
-- INDEXES FOR Doctor Table
-- ==========================================
CREATE INDEX idx_doctor_staff ON Doctor(StaffID);
CREATE INDEX idx_doctor_license ON Doctor(LicenseNo);

-- ==========================================
-- INDEXES FOR JMO Table
-- ==========================================
CREATE INDEX idx_jmo_doctor ON JMO(DoctorID);

-- ==========================================
-- INDEXES FOR Postmortem Table
-- ==========================================
CREATE INDEX idx_postmortem_case ON Postmortem(CaseID);
CREATE INDEX idx_postmortem_jmo ON Postmortem(JMO_ID);
CREATE INDEX idx_postmortem_date ON Postmortem(ExaminationDate);

-- ==========================================
-- INDEXES FOR Evidence Table
-- ==========================================
CREATE INDEX idx_evidence_case ON Evidence(CaseID);
CREATE INDEX idx_evidence_type ON Evidence(EvidenceType);
CREATE INDEX idx_evidence_collected_date ON Evidence(CollectedDate);

-- ==========================================
-- INDEXES FOR ChainOfCustody Table
-- ==========================================
CREATE INDEX idx_custody_evidence ON ChainOfCustody(EvidenceID);
CREATE INDEX idx_custody_staff ON ChainOfCustody(StaffID);
CREATE INDEX idx_custody_date ON ChainOfCustody(TransferDate);

-- ==========================================
-- INDEXES FOR LaboratoryTest Table
-- ==========================================
CREATE INDEX idx_test_evidence ON LaboratoryTest(EvidenceID);
CREATE INDEX idx_test_lab ON LaboratoryTest(LabID);
CREATE INDEX idx_test_date ON LaboratoryTest(TestDate);

-- ==========================================
-- INDEXES FOR CourtReport Table
-- ==========================================
CREATE INDEX idx_courtreport_case ON CourtReport(CaseID);
CREATE INDEX idx_courtreport_status ON CourtReport(Status);
CREATE INDEX idx_courtreport_date ON CourtReport(SubmissionDate);

-- ==========================================
-- INDEXES FOR CaseCourt Table
-- ==========================================
CREATE INDEX idx_casecourt_case ON CaseCourt(CaseID);
CREATE INDEX idx_casecourt_court ON CaseCourt(CourtID);

-- ==========================================
-- INDEXES FOR UserAccount Table
-- ==========================================
CREATE INDEX idx_user_username ON UserAccount(Username);
CREATE INDEX idx_user_role ON UserAccount(UserRole);
CREATE INDEX idx_user_staff ON UserAccount(StaffID);

-- ==========================================
-- INDEXES FOR AuditLog Table
-- ==========================================
CREATE INDEX idx_audit_user ON AuditLog(UserID);
CREATE INDEX idx_audit_date ON AuditLog(ActionDate);

-- ==========================================
-- INDEXES FOR Notification Table
-- ==========================================
CREATE INDEX idx_notification_user ON Notification(UserID);
CREATE INDEX idx_notification_status ON Notification(Status);
CREATE INDEX idx_notification_date ON Notification(CreatedDate);

-- ==========================================
-- INDEXES FOR DigitalSignature Table
-- ==========================================
CREATE INDEX idx_signature_report ON DigitalSignature(ReportID);
CREATE INDEX idx_signature_staff ON DigitalSignature(SignedBy);