-- ==========================================
-- VIEWS FOR ForensicMedicalDB
-- ==========================================

USE ForensicMedicalDB;

-- ==========================================
-- View: PatientCaseSummary
-- Shows patients with their forensic cases
-- ==========================================
CREATE OR REPLACE VIEW PatientCaseSummary AS
SELECT 
    p.PatientID,
    p.FullName,
    p.NIC,
    p.Gender,
    fc.CaseID,
    fc.CaseNumber,
    fc.CaseType,
    fc.Status,
    fc.IncidentDate,
    fc.CaseDescription
FROM Patient p
LEFT JOIN ForensicCase fc ON p.PatientID = fc.PatientID;

-- ==========================================
-- View: CaseDetailsWithPostmortem
-- Shows cases with postmortem details
-- ==========================================
CREATE OR REPLACE VIEW CaseDetailsWithPostmortem AS
SELECT 
    fc.CaseID,
    fc.CaseNumber,
    fc.CaseType,
    fc.Status,
    p.FullName AS PatientName,
    pm.PostmortemID,
    pm.ExaminationDate,
    pm.Findings,
    pm.CauseOfDeath,
    s.StaffName AS JMO_Name
FROM ForensicCase fc
JOIN Patient p ON fc.PatientID = p.PatientID
LEFT JOIN Postmortem pm ON fc.CaseID = pm.CaseID
LEFT JOIN JMO j ON pm.JMO_ID = j.JMO_ID
LEFT JOIN Doctor d ON j.DoctorID = d.DoctorID
LEFT JOIN Staff s ON d.StaffID = s.StaffID;

-- ==========================================
-- View: EvidenceWithLaboratoryResults
-- Shows evidence and lab test results
-- ==========================================
CREATE OR REPLACE VIEW EvidenceWithLaboratoryResults AS
SELECT 
    e.EvidenceID,
    e.EvidenceType,
    e.Description,
    e.StorageLocation,
    e.CollectedDate,
    lt.TestID,
    lt.TestType,
    lt.Result,
    lt.TestDate,
    l.LabName,
    l.Location AS LabLocation
FROM Evidence e
LEFT JOIN LaboratoryTest lt ON e.EvidenceID = lt.EvidenceID
LEFT JOIN Laboratory l ON lt.LabID = l.LabID;

-- ==========================================
-- View: ChainOfCustodyDetails
-- Shows chain of custody tracking
-- ==========================================
CREATE OR REPLACE VIEW ChainOfCustodyDetails AS
SELECT 
    coc.CustodyID,
    e.EvidenceID,
    e.EvidenceType,
    e.Description AS EvidenceDescription,
    s.StaffName AS HandledBy,
    s.Role AS StaffRole,
    coc.TransferDate,
    coc.ActionTaken
FROM ChainOfCustody coc
JOIN Evidence e ON coc.EvidenceID = e.EvidenceID
JOIN Staff s ON coc.StaffID = s.StaffID
ORDER BY coc.TransferDate DESC;

-- ==========================================
-- View: CourtCaseStatus
-- Shows court cases and their status
-- ==========================================
CREATE OR REPLACE VIEW CourtCaseStatus AS
SELECT 
    cr.CourtReportID,
    fc.CaseID,
    fc.CaseNumber,
    fc.CaseType,
    p.FullName AS PatientName,
    cr.SubmissionDate,
    cr.Status AS ReportStatus,
    cr.ReportContent,
    c.CourtName,
    c.Location AS CourtLocation,
    cc.HearingDate
FROM CourtReport cr
JOIN ForensicCase fc ON cr.CaseID = fc.CaseID
JOIN Patient p ON fc.PatientID = p.PatientID
LEFT JOIN CaseCourt cc ON fc.CaseID = cc.CaseID
LEFT JOIN Court c ON cc.CourtID = c.CourtID;

-- ==========================================
-- View: StaffWithRoles
-- Shows all staff and their assigned roles
-- ==========================================
CREATE OR REPLACE VIEW StaffWithRoles AS
SELECT 
    s.StaffID,
    s.StaffName,
    s.Role,
    s.ContactNo,
    s.Email,
    d.DoctorID,
    d.Specialization,
    d.LicenseNo,
    j.JMO_ID,
    j.Department
FROM Staff s
LEFT JOIN Doctor d ON s.StaffID = d.StaffID
LEFT JOIN JMO j ON d.DoctorID = j.DoctorID;

-- ==========================================
-- View: PatientHistoryOverview
-- Shows patient history summary
-- ==========================================
CREATE OR REPLACE VIEW PatientHistoryOverview AS
SELECT 
    p.PatientID,
    p.FullName,
    p.NIC,
    ph.HistoryID,
    ph.MedicalHistory,
    ph.PreviousCases,
    COUNT(fc.CaseID) AS TotalCases
FROM Patient p
JOIN PatientHistory ph ON p.PatientID = ph.PatientID
LEFT JOIN ForensicCase fc ON p.PatientID = fc.PatientID
GROUP BY p.PatientID, ph.HistoryID;

-- ==========================================
-- View: ActiveInvestigations
-- Shows currently active forensic cases
-- ==========================================
CREATE OR REPLACE VIEW ActiveInvestigations AS
SELECT 
    fc.CaseID,
    fc.CaseNumber,
    fc.CaseType,
    fc.IncidentDate,
    fc.IncidentLocation,
    p.FullName AS PatientName,
    COUNT(DISTINCT e.EvidenceID) AS EvidenceCount,
    COUNT(DISTINCT lt.TestID) AS TestsCompleted
FROM ForensicCase fc
JOIN Patient p ON fc.PatientID = p.PatientID
LEFT JOIN Evidence e ON fc.CaseID = e.CaseID
LEFT JOIN LaboratoryTest lt ON e.EvidenceID = lt.EvidenceID
WHERE fc.Status IN ('Open', 'Pending', 'Under Investigation')
GROUP BY fc.CaseID, p.FullName;

-- ==========================================
-- View: AuditTrailSummary
-- Shows user activity audit log
-- ==========================================
CREATE OR REPLACE VIEW AuditTrailSummary AS
SELECT 
    a.AuditID,
    u.Username,
    u.UserRole,
    a.Action,
    a.ActionDate,
    s.StaffName
FROM AuditLog a
JOIN UserAccount u ON a.UserID = u.UserID
LEFT JOIN Staff s ON u.StaffID = s.StaffID
ORDER BY a.ActionDate DESC;