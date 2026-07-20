-- ==========================================
-- CONSTRAINTS FOR ForensicMedicalDB
-- ==========================================

USE ForensicMedicalDB;

-- ==========================================
-- PRIMARY KEYS (Already defined in CREATE TABLE)
-- All tables already have PRIMARY KEY defined
-- ==========================================

-- ==========================================
-- FOREIGN KEYS (Already defined in CREATE TABLE)
-- All foreign keys are already defined
-- ==========================================

-- ==========================================
-- CHECK CONSTRAINTS
-- ==========================================

-- Add CHECK constraints for gender validation
ALTER TABLE Patient 
ADD CONSTRAINT chk_patient_gender 
CHECK (Gender IN ('Male', 'Female', 'Other'));

-- Add CHECK constraint for case status
ALTER TABLE ForensicCase 
ADD CONSTRAINT chk_case_status 
CHECK (Status IN ('Open', 'Closed', 'Pending', 'Under Investigation', 'In Progress', 'Scheduled', 'Active'));

-- Add CHECK constraint for sample status
ALTER TABLE EvidenceSample 
ADD CONSTRAINT chk_sample_status 
CHECK (SampleStatus IN ('Collected', 'In Transit', 'In Lab', 'Analyzed', 'Returned','Received', 'Stored', 'Verified', 'Testing'));

-- Add CHECK constraint for report status
ALTER TABLE CourtReport 
ADD CONSTRAINT chk_court_report_status 
CHECK (Status IN ('Draft', 'Submitted', 'Accepted', 'Rejected', 'Pending'));

-- Add CHECK constraint for notification status
ALTER TABLE Notification 
ADD CONSTRAINT chk_notification_status 
CHECK (Status IN ('Read', 'Unread', 'Archived'));

-- Add CHECK constraint for backup status
ALTER TABLE BackupRecord 
ADD CONSTRAINT chk_backup_status 
CHECK (Status IN ('Successful', 'Failed', 'In Progress', 'Completed'));

-- Add CHECK constraint for staff role
ALTER TABLE Staff 
ADD CONSTRAINT chk_staff_role 
CHECK (Role IN ('Doctor', 'JMO', 'Lab Technician', 'Administrator', 'Forensic Expert'));

-- Add CHECK constraint for user role
ALTER TABLE UserAccount 
ADD CONSTRAINT chk_user_role 
CHECK (UserRole IN ('Administrator', 'Doctor', 'JMO', 'Lab Technician', 'Staff', 'Evidence Officer'));

-- ==========================================
-- UNIQUE CONSTRAINTS (Additional)
-- ==========================================

-- Add UNIQUE constraint for Doctor License Number
ALTER TABLE Doctor 
ADD CONSTRAINT unique_doctor_license 
UNIQUE (LicenseNo);

-- Add UNIQUE constraint for Staff Email
ALTER TABLE Staff 
ADD CONSTRAINT unique_staff_email 
UNIQUE (Email);

-- Add UNIQUE constraint for Case Number (already defined, but adding explicit)
ALTER TABLE ForensicCase 
ADD CONSTRAINT unique_case_number 
UNIQUE (CaseNumber);

-- Add UNIQUE constraint for Username (already defined)
ALTER TABLE UserAccount 
ADD CONSTRAINT unique_username 
UNIQUE (Username);

-- ==========================================
-- DEFAULT CONSTRAINTS (Using ALTER MODIFY)
-- ==========================================

-- Set default values for various columns using ALTER MODIFY
ALTER TABLE Patient 
MODIFY COLUMN RegistrationDate DATE DEFAULT NULL;

ALTER TABLE ForensicCase 
MODIFY COLUMN Status VARCHAR(30) DEFAULT 'Pending';

ALTER TABLE ExaminationReport 
MODIFY COLUMN CreatedDate DATE DEFAULT NULL;

ALTER TABLE CourtReport 
MODIFY COLUMN Status VARCHAR(50) DEFAULT 'Draft';

ALTER TABLE Evidence 
MODIFY COLUMN CollectedDate DATE DEFAULT NULL;

ALTER TABLE LaboratoryTest 
MODIFY COLUMN TestDate DATE DEFAULT NULL;

ALTER TABLE Notification 
MODIFY COLUMN Status VARCHAR(20) DEFAULT 'Unread';

ALTER TABLE BackupRecord 
MODIFY COLUMN Status VARCHAR(50) DEFAULT 'In Progress';

ALTER TABLE AuditLog 
MODIFY COLUMN ActionDate DATETIME DEFAULT NULL;

ALTER TABLE UserAccount 
MODIFY COLUMN UserRole VARCHAR(50) DEFAULT 'Staff';

ALTER TABLE ChainOfCustody 
MODIFY COLUMN ActionTaken VARCHAR(100) DEFAULT 'Transferred';

ALTER TABLE EvidenceSample 
MODIFY COLUMN SampleStatus VARCHAR(50) DEFAULT 'Collected';

-- Add DEFAULT for Postmortem ExaminationDate
ALTER TABLE Postmortem 
MODIFY COLUMN ExaminationDate DATE DEFAULT NULL;

-- Add DEFAULT for DigitalSignature SignedDate
ALTER TABLE DigitalSignature 
MODIFY COLUMN SignedDate DATE DEFAULT NULL;

-- ==========================================
-- ALTERNATIVE: Using ALTER SET DEFAULT (MySQL 8.0+)
-- ==========================================
-- Note: If you're using MySQL 8.0+, you can use SET DEFAULT
-- But MODIFY COLUMN is more compatible across versions

-- ==========================================
-- VIEW ALL CONSTRAINTS FOR VERIFICATION
-- ==========================================

-- Check all constraints on the database
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'ForensicMedicalDB'
ORDER BY TABLE_NAME, CONSTRAINT_TYPE;

-- Check all CHECK constraints
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'ForensicMedicalDB';

-- Check all DEFAULT values
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_DEFAULT,
    DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ForensicMedicalDB'
  AND COLUMN_DEFAULT IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;