-- ==========================================
-- STORED PROCEDURES FOR ForensicMedicalDB
-- ==========================================

USE ForensicMedicalDB;

DELIMITER $$

-- ==========================================
-- Procedure: AddNewPatient
-- Adds a new patient and their initial history
-- ==========================================
CREATE PROCEDURE AddNewPatient(
    IN p_FullName VARCHAR(100),
    IN p_NIC VARCHAR(20),
    IN p_DateOfBirth DATE,
    IN p_Gender VARCHAR(10),
    IN p_Address VARCHAR(255),
    IN p_ContactNo VARCHAR(15),
    IN p_MedicalHistory TEXT,
    IN p_PreviousCases TEXT,
    OUT p_PatientID INT
)
BEGIN
    -- Insert patient
    INSERT INTO Patient(
        FullName, NIC, DateOfBirth, Gender, Address, ContactNo, RegistrationDate
    ) VALUES (
        p_FullName, p_NIC, p_DateOfBirth, p_Gender, p_Address, p_ContactNo, CURDATE()
    );
    
    SET p_PatientID = LAST_INSERT_ID();
    
    -- Insert patient history
    INSERT INTO PatientHistory(
        PatientID, MedicalHistory, PreviousCases
    ) VALUES (
        p_PatientID, p_MedicalHistory, p_PreviousCases
    );
END$$

-- ==========================================
-- Procedure: CreateForensicCase
-- Creates a new forensic case
-- ==========================================
CREATE PROCEDURE CreateForensicCase(
    IN p_PatientID INT,
    IN p_CaseType VARCHAR(50),
    IN p_IncidentDate DATE,
    IN p_IncidentLocation VARCHAR(200),
    IN p_CaseDescription TEXT,
    IN p_Status VARCHAR(30),
    OUT p_CaseID INT
)
BEGIN
    DECLARE v_CaseNumber VARCHAR(50);
    
    -- Generate case number (Year-Month-Sequence)
    SET v_CaseNumber = CONCAT(
        YEAR(CURDATE()), '-',
        LPAD(MONTH(CURDATE()), 2, '0'), '-',
        LPAD((SELECT COUNT(*) + 1 FROM ForensicCase), 4, '0')
    );
    
    INSERT INTO ForensicCase(
        PatientID, CaseNumber, CaseType, IncidentDate, 
        IncidentLocation, CaseDescription, Status
    ) VALUES (
        p_PatientID, v_CaseNumber, p_CaseType, p_IncidentDate,
        p_IncidentLocation, p_CaseDescription, p_Status
    );
    
    SET p_CaseID = LAST_INSERT_ID();
END$$

-- ==========================================
-- Procedure: UpdateCaseStatus
-- Updates the status of a forensic case
-- ==========================================
CREATE PROCEDURE UpdateCaseStatus(
    IN p_CaseID INT,
    IN p_NewStatus VARCHAR(30)
)
BEGIN
    UPDATE ForensicCase 
    SET Status = p_NewStatus 
    WHERE CaseID = p_CaseID;
END$$

-- ==========================================
-- Procedure: AddEvidenceToCase
-- Adds new evidence to a case
-- ==========================================
CREATE PROCEDURE AddEvidenceToCase(
    IN p_CaseID INT,
    IN p_EvidenceType VARCHAR(100),
    IN p_Description TEXT,
    IN p_StorageLocation VARCHAR(100),
    IN p_CollectedDate DATE,
    OUT p_EvidenceID INT
)
BEGIN
    INSERT INTO Evidence(
        CaseID, EvidenceType, Description, StorageLocation, CollectedDate
    ) VALUES (
        p_CaseID, p_EvidenceType, p_Description, p_StorageLocation, 
        IFNULL(p_CollectedDate, CURDATE())
    );
    
    SET p_EvidenceID = LAST_INSERT_ID();
END$$

-- ==========================================
-- Procedure: RecordChainOfCustody
-- Records chain of custody for evidence
-- ==========================================
CREATE PROCEDURE RecordChainOfCustody(
    IN p_EvidenceID INT,
    IN p_StaffID INT,
    IN p_ActionTaken VARCHAR(100)
)
BEGIN
    INSERT INTO ChainOfCustody(
        EvidenceID, StaffID, TransferDate, ActionTaken
    ) VALUES (
        p_EvidenceID, p_StaffID, CURDATE(), p_ActionTaken
    );
END$$

-- ==========================================
-- Procedure: GetCasesByDateRange
-- Retrieves cases within a date range
-- ==========================================
CREATE PROCEDURE GetCasesByDateRange(
    IN p_StartDate DATE,
    IN p_EndDate DATE
)
BEGIN
    SELECT 
        c.CaseID, c.CaseNumber, c.CaseType, c.Status,
        p.FullName AS PatientName,
        c.IncidentDate, c.IncidentLocation
    FROM ForensicCase c
    JOIN Patient p ON c.PatientID = p.PatientID
    WHERE c.IncidentDate BETWEEN p_StartDate AND p_EndDate
    ORDER BY c.IncidentDate DESC;
END$$

-- ==========================================
-- Procedure: GetEvidenceByCase
-- Retrieves all evidence for a case
-- ==========================================
CREATE PROCEDURE GetEvidenceByCase(
    IN p_CaseID INT
)
BEGIN
    SELECT 
        e.EvidenceID,
        e.EvidenceType,
        e.Description,
        e.StorageLocation,
        e.CollectedDate,
        es.SampleID,
        es.SampleType,
        es.SampleStatus,
        lt.TestID,
        lt.TestType,
        lt.Result,
        lt.TestDate
    FROM Evidence e
    LEFT JOIN EvidenceSample es ON e.EvidenceID = es.EvidenceID
    LEFT JOIN LaboratoryTest lt ON e.EvidenceID = lt.EvidenceID
    WHERE e.CaseID = p_CaseID;
END$$

-- ==========================================
-- Procedure: CreateUserAccount
-- Creates a new user account
-- ==========================================
CREATE PROCEDURE CreateUserAccount(
    IN p_Username VARCHAR(50),
    IN p_Password VARCHAR(255),
    IN p_UserRole VARCHAR(50),
    IN p_StaffID INT,
    OUT p_UserID INT
)
BEGIN
    INSERT INTO UserAccount(
        Username, Password, UserRole, StaffID
    ) VALUES (
        p_Username, p_Password, p_UserRole, p_StaffID
    );
    
    SET p_UserID = LAST_INSERT_ID();
END$$

-- ==========================================
-- Procedure: LogUserAction
-- Logs user actions in audit log
-- ==========================================
CREATE PROCEDURE LogUserAction(
    IN p_UserID INT,
    IN p_Action VARCHAR(100)
)
BEGIN
    INSERT INTO AuditLog(
        UserID, Action, ActionDate
    ) VALUES (
        p_UserID, p_Action, CURRENT_TIMESTAMP
    );
END$$

-- ==========================================
-- Procedure: GetCaseStatistics
-- Returns statistics about cases
-- ==========================================
CREATE PROCEDURE GetCaseStatistics()
BEGIN
    SELECT 
        COUNT(*) AS TotalCases,
        SUM(CASE WHEN Status = 'Open' THEN 1 ELSE 0 END) AS OpenCases,
        SUM(CASE WHEN Status = 'Closed' THEN 1 ELSE 0 END) AS ClosedCases,
        SUM(CASE WHEN Status = 'Pending' THEN 1 ELSE 0 END) AS PendingCases,
        COUNT(DISTINCT CaseType) AS CaseTypes,
        MIN(IncidentDate) AS OldestCase,
        MAX(IncidentDate) AS NewestCase
    FROM ForensicCase;
END$$

DELIMITER ;