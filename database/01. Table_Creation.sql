-- ==========================================
-- Create Database
-- ==========================================
CREATE DATABASE ForensicMedicalDB;
USE ForensicMedicalDB;
-- DROP DATABASE ForensicMedicalDB;

-- ==========================================
-- Patient Table
-- ==========================================
CREATE TABLE Patient(
    PatientID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(100) NOT NULL,
    NIC VARCHAR(20) UNIQUE,
    DateOfBirth DATE,
    Gender VARCHAR(10),
    Address VARCHAR(255),
    ContactNo VARCHAR(15),
    RegistrationDate DATE
);

-- ==========================================
-- PatientHistory Table
-- ==========================================
CREATE TABLE PatientHistory(
    HistoryID INT AUTO_INCREMENT PRIMARY KEY,
    PatientID INT,
    MedicalHistory TEXT,
    PreviousCases TEXT,
    FOREIGN KEY(PatientID) REFERENCES Patient(PatientID)
);

-- ==========================================
-- ForensicCase Table
-- ==========================================
CREATE TABLE ForensicCase(
    CaseID INT AUTO_INCREMENT PRIMARY KEY,
    PatientID INT,
    CaseNumber VARCHAR(50) UNIQUE,
    CaseType VARCHAR(50),
    IncidentDate DATE,
    IncidentLocation VARCHAR(200),
    CaseDescription TEXT,
    Status VARCHAR(30),
    FOREIGN KEY(PatientID) REFERENCES Patient(PatientID)
);

-- ==========================================
-- Incident Table
-- ==========================================
CREATE TABLE Incident(
    IncidentID INT AUTO_INCREMENT PRIMARY KEY,
    CaseID INT,
    IncidentType VARCHAR(100),
    PoliceStation VARCHAR(100),
    Description TEXT,
    FOREIGN KEY(CaseID) REFERENCES ForensicCase(CaseID)
);

-- ==========================================
-- Staff Table
-- ==========================================
CREATE TABLE Staff(
    StaffID INT AUTO_INCREMENT PRIMARY KEY,
    StaffName VARCHAR(100),
    Role VARCHAR(50),
    ContactNo VARCHAR(15),
    Email VARCHAR(100)
);

-- ==========================================
-- Doctor Table
-- ==========================================
CREATE TABLE Doctor(
    DoctorID INT AUTO_INCREMENT PRIMARY KEY,
    StaffID INT,
    Specialization VARCHAR(100),
    LicenseNo VARCHAR(50),
    FOREIGN KEY(StaffID) REFERENCES Staff(StaffID)
);

-- ==========================================
-- JudicialMedicalOfficer Table
-- ==========================================
CREATE TABLE JMO(
    JMO_ID INT AUTO_INCREMENT PRIMARY KEY,
    DoctorID INT,
    Department VARCHAR(100),
    FOREIGN KEY(DoctorID) REFERENCES Doctor(DoctorID)
);

-- ==========================================
-- Postmortem Table
-- ==========================================
CREATE TABLE Postmortem(
    PostmortemID INT AUTO_INCREMENT PRIMARY KEY,
    CaseID INT,
    JMO_ID INT,
    ExaminationDate DATE,
    Findings TEXT,
    CauseOfDeath VARCHAR(255),
    FOREIGN KEY(CaseID) REFERENCES ForensicCase(CaseID),
    FOREIGN KEY(JMO_ID) REFERENCES JMO(JMO_ID)
);

-- ==========================================
-- ExaminationReport Table
-- ==========================================
CREATE TABLE ExaminationReport(
    ReportID INT AUTO_INCREMENT PRIMARY KEY,
    PostmortemID INT,
    ReportDetails TEXT,
    CreatedDate DATE,
    FOREIGN KEY(PostmortemID) REFERENCES Postmortem(PostmortemID)
);

-- ==========================================
-- Evidence Table
-- ==========================================
CREATE TABLE Evidence(
    EvidenceID INT AUTO_INCREMENT PRIMARY KEY,
    CaseID INT,
    EvidenceType VARCHAR(100),
    Description TEXT,
    StorageLocation VARCHAR(100),
    CollectedDate DATE,
    FOREIGN KEY(CaseID) REFERENCES ForensicCase(CaseID)
);

-- ==========================================
-- EvidenceSample Table
-- ==========================================
CREATE TABLE EvidenceSample(
    SampleID INT AUTO_INCREMENT PRIMARY KEY,
    EvidenceID INT,
    SampleType VARCHAR(100),
    SampleStatus VARCHAR(50),
    FOREIGN KEY(EvidenceID) REFERENCES Evidence(EvidenceID)
);

-- ==========================================
-- ChainOfCustody Table
-- ==========================================
CREATE TABLE ChainOfCustody(
    CustodyID INT AUTO_INCREMENT PRIMARY KEY,
    EvidenceID INT,
    StaffID INT,
    TransferDate DATE,
    ActionTaken VARCHAR(100),
    FOREIGN KEY(EvidenceID) REFERENCES Evidence(EvidenceID),
    FOREIGN KEY(StaffID) REFERENCES Staff(StaffID)
);

-- ==========================================
-- Laboratory Table
-- ==========================================
CREATE TABLE Laboratory(
    LabID INT AUTO_INCREMENT PRIMARY KEY,
    LabName VARCHAR(100),
    Location VARCHAR(200)
);

-- ==========================================
-- LaboratoryTest Table
-- ==========================================
CREATE TABLE LaboratoryTest(
    TestID INT AUTO_INCREMENT PRIMARY KEY,
    EvidenceID INT,
    LabID INT,
    TestType VARCHAR(100),
    Result TEXT,
    TestDate DATE,
    FOREIGN KEY(EvidenceID) REFERENCES Evidence(EvidenceID),
    FOREIGN KEY(LabID) REFERENCES Laboratory(LabID)
);

-- ==========================================
-- CourtReport Table
-- ==========================================
CREATE TABLE CourtReport(
    CourtReportID INT AUTO_INCREMENT PRIMARY KEY,
    CaseID INT,
    SubmissionDate DATE,
    Status VARCHAR(50),
    ReportContent TEXT,
    FOREIGN KEY(CaseID) REFERENCES ForensicCase(CaseID)
);

-- ==========================================
-- Court Table
-- ==========================================
CREATE TABLE Court(
    CourtID INT AUTO_INCREMENT PRIMARY KEY,
    CourtName VARCHAR(100),
    Location VARCHAR(100)
);

-- ==========================================
-- CaseCourt Table
-- ==========================================
CREATE TABLE CaseCourt(
    CaseCourtID INT AUTO_INCREMENT PRIMARY KEY,
    CaseID INT,
    CourtID INT,
    HearingDate DATE,
    FOREIGN KEY(CaseID) REFERENCES ForensicCase(CaseID),
    FOREIGN KEY(CourtID) REFERENCES Court(CourtID)
);

-- ==========================================
-- UserAccount Table
-- ==========================================
CREATE TABLE UserAccount(
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(50) UNIQUE,
    Password VARCHAR(255),
    UserRole VARCHAR(50),
    StaffID INT,
    FOREIGN KEY(StaffID) REFERENCES Staff(StaffID)
);

-- ==========================================
-- Role Table
-- ==========================================
CREATE TABLE Role(
    RoleID INT AUTO_INCREMENT PRIMARY KEY,
    RoleName VARCHAR(50)
);

-- ==========================================
-- Permission Table
-- ==========================================
CREATE TABLE Permission(
    PermissionID INT AUTO_INCREMENT PRIMARY KEY,
    PermissionName VARCHAR(100)
);

-- ==========================================
-- RolePermission Table
-- ==========================================
CREATE TABLE RolePermission(
    RolePermissionID INT AUTO_INCREMENT PRIMARY KEY,
    RoleID INT,
    PermissionID INT,
    FOREIGN KEY(RoleID) REFERENCES Role(RoleID),
    FOREIGN KEY(PermissionID) REFERENCES Permission(PermissionID)
);

-- ==========================================
-- AuditLog Table
-- ==========================================
CREATE TABLE AuditLog(
    AuditID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    Action VARCHAR(100),
    ActionDate DATETIME,
    FOREIGN KEY(UserID) REFERENCES UserAccount(UserID)
);

-- ==========================================
-- Notification Table
-- ==========================================
CREATE TABLE Notification(
    NotificationID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    Message TEXT,
    CreatedDate DATETIME,
    Status VARCHAR(20),
    FOREIGN KEY(UserID) REFERENCES UserAccount(UserID)
);

-- ==========================================
-- DigitalSignature Table
-- ==========================================
CREATE TABLE DigitalSignature(
    SignatureID INT AUTO_INCREMENT PRIMARY KEY,
    ReportID INT,
    SignedBy INT,
    SignatureData TEXT,
    SignedDate DATE,
    FOREIGN KEY(ReportID) REFERENCES CourtReport(CourtReportID),
    FOREIGN KEY(SignedBy) REFERENCES Staff(StaffID)
);

-- ==========================================
-- BackupRecord Table
-- ==========================================
CREATE TABLE BackupRecord(
    BackupID INT AUTO_INCREMENT PRIMARY KEY,
    BackupDate DATETIME,
    Location VARCHAR(255),
    Status VARCHAR(50)
);

SHOW TABLES;




