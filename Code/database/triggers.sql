-- ==========================================
-- TRIGGERS FOR ForensicMedicalDB
-- ==========================================

USE ForensicMedicalDB;

DELIMITER $$

-- ==========================================
-- Trigger: UpdateAuditLogOnUserAction
-- Automatically logs INSERT, UPDATE, DELETE operations
-- ==========================================
CREATE TRIGGER log_forensic_case_insert
AFTER INSERT ON ForensicCase
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog(UserID, Action, ActionDate)
    VALUES (1, CONCAT('Case Created: ', NEW.CaseNumber), CURRENT_TIMESTAMP);
END$$

-- ==========================================
-- Trigger: UpdateCaseStatusChangeLog
-- Logs when case status is updated
-- ==========================================
CREATE TRIGGER log_case_status_update
BEFORE UPDATE ON ForensicCase
FOR EACH ROW
BEGIN
    IF OLD.Status != NEW.Status THEN
        INSERT INTO AuditLog(UserID, Action, ActionDate)
        VALUES (1, CONCAT('Case Status Changed: ', OLD.CaseNumber, 
                         ' from ', OLD.Status, ' to ', NEW.Status), 
                CURRENT_TIMESTAMP);
    END IF;
END$$

-- ==========================================
-- Trigger: AutoCreatePatientHistory
-- Automatically creates patient history on new patient
-- ==========================================
CREATE TRIGGER create_patient_history
AFTER INSERT ON Patient
FOR EACH ROW
BEGIN
    INSERT INTO PatientHistory(PatientID, MedicalHistory, PreviousCases)
    VALUES (NEW.PatientID, 'Initial record created', NULL);
END$$

-- ==========================================
-- Trigger: UpdateNotificationOnNewCase
-- Creates notification when new case is created
-- ==========================================
CREATE TRIGGER notify_new_case
AFTER INSERT ON ForensicCase
FOR EACH ROW
BEGIN
    -- Notify admins (assuming UserID 1 is admin)
    INSERT INTO Notification(UserID, Message, CreatedDate, Status)
    VALUES (1, CONCAT('New forensic case created: ', NEW.CaseNumber, 
                     ' - ', NEW.CaseType), CURRENT_TIMESTAMP, 'Unread');
END$$

-- ==========================================
-- Trigger: UpdateEvidenceOnTest
-- Updates evidence sample status when lab test is performed
-- ==========================================
CREATE TRIGGER update_evidence_status_on_test
AFTER INSERT ON LaboratoryTest
FOR EACH ROW
BEGIN
    -- Update evidence sample status
    UPDATE EvidenceSample 
    SET SampleStatus = 'Analyzed' 
    WHERE EvidenceID = NEW.EvidenceID;
    
    -- Log the test
    INSERT INTO AuditLog(UserID, Action, ActionDate)
    VALUES (1, CONCAT('Lab Test Performed on Evidence ID: ', NEW.EvidenceID), 
            CURRENT_TIMESTAMP);
END$$

-- ==========================================
-- Trigger: UpdateCustodyOnTransfer
-- Logs chain of custody transfers
-- ==========================================
CREATE TRIGGER log_custody_transfer
AFTER INSERT ON ChainOfCustody
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog(UserID, Action, ActionDate)
    VALUES (1, CONCAT('Evidence Transfer: Evidence ID ', NEW.EvidenceID, 
                     ' - ', NEW.ActionTaken), CURRENT_TIMESTAMP);
END$$

-- ==========================================
-- Trigger: PreventDuplicateEvidence
-- Prevents adding duplicate evidence to same case
-- ==========================================
CREATE TRIGGER check_duplicate_evidence
BEFORE INSERT ON Evidence
FOR EACH ROW
BEGIN
    DECLARE duplicate_count INT;
    
    SELECT COUNT(*) INTO duplicate_count
    FROM Evidence
    WHERE CaseID = NEW.CaseID 
      AND EvidenceType = NEW.EvidenceType
      AND Description = NEW.Description;
    
    IF duplicate_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Duplicate evidence already exists for this case';
    END IF;
END$$

-- ==========================================
-- Trigger: UpdateBackupRecord
-- Automatically updates backup record when backup is created
-- ==========================================
CREATE TRIGGER backup_status_update
AFTER UPDATE ON BackupRecord
FOR EACH ROW
BEGIN
    IF OLD.Status != NEW.Status AND NEW.Status = 'Successful' THEN
        INSERT INTO AuditLog(UserID, Action, ActionDate)
        VALUES (1, CONCAT('Backup Successful: ', NEW.BackupID, 
                         ' at ', NEW.Location), CURRENT_TIMESTAMP);
    END IF;
END$$

-- ==========================================
-- Trigger: ValidateUserRole
-- Validates user role on insertion
-- ==========================================
CREATE TRIGGER validate_user_role
BEFORE INSERT ON UserAccount
FOR EACH ROW
BEGIN
    DECLARE valid_role INT;
    
    SELECT COUNT(*) INTO valid_role
    FROM Role
    WHERE RoleName = NEW.UserRole;
    
    IF valid_role = 0 THEN
        SET NEW.UserRole = 'Staff';
    END IF;
END$$

-- ==========================================
-- Trigger: CourtReportSubmission
-- Creates notification when court report is submitted
-- ==========================================
CREATE TRIGGER notify_court_report
AFTER INSERT ON CourtReport
FOR EACH ROW
BEGIN
    INSERT INTO Notification(UserID, Message, CreatedDate, Status)
    SELECT 
        u.UserID,
        CONCAT('Court report submitted for Case ID: ', NEW.CaseID),
        CURRENT_TIMESTAMP,
        'Unread'
    FROM UserAccount u
    WHERE u.UserRole = 'Administrator'
    LIMIT 1;
END$$

-- ==========================================
-- Trigger: LogDigitalSignature
-- Logs when digital signature is applied
-- ==========================================
CREATE TRIGGER log_digital_signature
AFTER INSERT ON DigitalSignature
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog(UserID, Action, ActionDate)
    VALUES (NEW.SignedBy, 
            CONCAT('Signed Court Report ID: ', NEW.ReportID), 
            CURRENT_TIMESTAMP);
END$$

-- ==========================================
-- Trigger: UpdatePostmortemDate
-- Automatically updates postmortem examination date if null
-- ==========================================
CREATE TRIGGER set_postmortem_date
BEFORE INSERT ON Postmortem
FOR EACH ROW
BEGIN
    IF NEW.ExaminationDate IS NULL THEN
        SET NEW.ExaminationDate = CURDATE();
    END IF;
END$$

DELIMITER ;