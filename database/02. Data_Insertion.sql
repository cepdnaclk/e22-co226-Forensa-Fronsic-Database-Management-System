USE ForensicMedicalDB;

-- ==========================================
-- Patient
-- ==========================================
INSERT INTO Patient
(FullName, NIC, DateOfBirth, Gender, Address, ContactNo, RegistrationDate)
VALUES
('Nimal Perera','901234567V','1990-05-12','Male','Colombo','0711111111','2026-01-10'),
('Kumari Silva','921234568V','1992-08-20','Female','Kandy','0722222222','2026-01-15'),
('Sunil Fernando','851234569V','1985-02-18','Male','Galle','0773333333','2026-02-01'),
('Anjali Jayasinghe','951234570V','1995-11-10','Female','Kurunegala','0764444444','2026-02-12'),
('Kasun Wijesinghe','881234571V','1988-04-30','Male','Negombo','0755555555','2026-03-05');

-- ==========================================
-- PatientHistory
-- ==========================================
INSERT INTO PatientHistory
(PatientID, MedicalHistory, PreviousCases)
VALUES
(1,'No chronic illness','None'),
(2,'Asthma','Minor assault case'),
(3,'Diabetes','Traffic accident'),
(4,'Healthy','None'),
(5,'Hypertension','Domestic violence investigation');

-- ==========================================
-- Staff
-- ==========================================
INSERT INTO Staff
(StaffName, Role, ContactNo, Email)
VALUES
('Dr. Samantha Perera','Doctor','0719000001','sam@fmh.lk'),
('Dr. Nadeesha Silva','Doctor','0719000002','nadeesha@fmh.lk'),
('Kasun Gunawardena','Lab Technician','0719000003','kasun@fmh.lk'),
('Ruwan Fernando','Evidence Officer','0719000004','ruwan@fmh.lk'),
('Nimali Jayawardena','Administrator','0719000005','nimali@fmh.lk');

-- ==========================================
-- Doctor
-- ==========================================
INSERT INTO Doctor
(StaffID, Specialization, LicenseNo)
VALUES
(1,'Forensic Medicine','SLMC1001'),
(2,'Pathology','SLMC1002');

-- ==========================================
-- JMO
-- ==========================================
INSERT INTO JMO
(DoctorID, Department)
VALUES
(1,'Judicial Medical Unit'),
(2,'Forensic Pathology Unit');

-- ==========================================
-- Laboratory
-- ==========================================
INSERT INTO Laboratory
(LabName, Location)
VALUES
('Central Forensic Laboratory','Colombo'),
('DNA Analysis Laboratory','Kandy'),
('Toxicology Laboratory','Galle');

-- ==========================================
-- ForensicCase
-- ==========================================
INSERT INTO ForensicCase
(PatientID, CaseNumber, CaseType, IncidentDate, IncidentLocation, CaseDescription, Status)
VALUES
(1,'FC001','Homicide','2026-01-12','Colombo','Suspected homicide investigation','Open'),
(2,'FC002','Assault','2026-01-18','Kandy','Physical assault case','Under Investigation'),
(3,'FC003','Traffic Accident','2026-02-05','Galle','Fatal road accident','Closed'),
(4,'FC004','Suicide','2026-02-15','Kurunegala','Suspected suicide','Open'),
(5,'FC005','Poisoning','2026-03-10','Negombo','Poisoning investigation','Pending');

-- ==========================================
-- Incident
-- ==========================================
INSERT INTO Incident
(CaseID, IncidentType, PoliceStation, Description)
VALUES
(1,'Murder','Colombo Central Police','Victim found in residence'),
(2,'Assault','Kandy Police','Fight reported'),
(3,'Road Accident','Galle Police','Collision involving two vehicles'),
(4,'Suicide','Kurunegala Police','Body recovered at home'),
(5,'Poisoning','Negombo Police','Possible toxic substance');

-- ==========================================
-- Postmortem
-- ==========================================
INSERT INTO Postmortem
(CaseID, JMO_ID, ExaminationDate, Findings, CauseOfDeath)
VALUES
(1,1,'2026-01-13','Multiple stab wounds','Hemorrhagic shock'),
(3,2,'2026-02-06','Severe head injuries','Head trauma'),
(4,1,'2026-02-16','Ligature mark present','Asphyxia'),
(5,2,'2026-03-11','Poison detected','Chemical poisoning');

-- ==========================================
-- ExaminationReport
-- ==========================================
INSERT INTO ExaminationReport
(PostmortemID, ReportDetails, CreatedDate)
VALUES
(1,'Complete postmortem report submitted.','2026-01-14'),
(2,'Traffic accident findings recorded.','2026-02-07'),
(3,'Suicide examination completed.','2026-02-17'),
(4,'Toxicology report attached.','2026-03-12');

-- ==========================================
-- Evidence
-- ==========================================
INSERT INTO Evidence
(CaseID, EvidenceType, Description, StorageLocation, CollectedDate)
VALUES
(1,'Knife','Blood stained knife','Locker A1','2026-01-12'),
(1,'Clothing','Victim clothing','Locker A2','2026-01-12'),
(2,'Photographs','Crime scene photos','Digital Archive','2026-01-18'),
(3,'Vehicle Parts','Broken bumper','Warehouse B','2026-02-05'),
(5,'Blood Sample','Victim blood sample','Cold Storage','2026-03-10');

-- ==========================================
-- EvidenceSample
-- ==========================================
INSERT INTO EvidenceSample
(EvidenceID, SampleType, SampleStatus)
VALUES
(1,'Blood','Received'),
(2,'Fabric','Stored'),
(3,'Digital','Verified'),
(4,'Metal','Testing'),
(5,'Blood','Testing');

-- ==========================================
-- ChainOfCustody
-- ==========================================
INSERT INTO ChainOfCustody
(EvidenceID, StaffID, TransferDate, ActionTaken)
VALUES
(1,4,'2026-01-12','Collected'),
(2,4,'2026-01-13','Transferred to storage'),
(3,5,'2026-01-18','Archived'),
(4,4,'2026-02-05','Sent for examination'),
(5,3,'2026-03-10','Delivered to laboratory');

-- ==========================================
-- LaboratoryTest
-- ==========================================
INSERT INTO LaboratoryTest
(EvidenceID, LabID, TestType, Result, TestDate)
VALUES
(1,1,'DNA Analysis','DNA matched suspect','2026-01-15'),
(2,1,'Fiber Analysis','Fibers identified','2026-01-16'),
(4,2,'Material Analysis','Vehicle paint matched','2026-02-07'),
(5,3,'Toxicology','Poison detected','2026-03-12');

-- ==========================================
-- Court
-- ==========================================
INSERT INTO Court
(CourtName, Location)
VALUES
('Colombo High Court','Colombo'),
('Kandy High Court','Kandy'),
('Galle High Court','Galle');

-- ==========================================
-- CourtReport
-- ==========================================
INSERT INTO CourtReport
(CaseID, SubmissionDate, Status, ReportContent)
VALUES
(1,'2026-01-20','Submitted','Final forensic report submitted to Colombo High Court.'),
(2,'2026-01-25','Pending','Assault investigation report awaiting approval.'),
(3,'2026-02-10','Submitted','Traffic accident forensic report submitted.'),
(4,'2026-02-20','Draft','Suicide investigation report under review.'),
(5,'2026-03-15','Submitted','Poisoning investigation report submitted.');

-- ==========================================
-- CaseCourt
-- ==========================================
INSERT INTO CaseCourt
(CaseID, CourtID, HearingDate)
VALUES
(1,1,'2026-02-05'),
(2,2,'2026-02-10'),
(3,3,'2026-02-25'),
(4,2,'2026-03-05'),
(5,1,'2026-03-25');

-- ==========================================
-- UserAccount
-- ==========================================
INSERT INTO UserAccount
(Username, Password, UserRole, StaffID)
VALUES
('admin','admin123','Administrator',5),
('jmo1','jmo123','JMO',1),
('doctor2','doctor123','Doctor',2),
('labtech','lab123','Lab Technician',3),
('evidence1','evidence123','Evidence Officer',4);

-- ==========================================
-- Role
-- ==========================================
INSERT INTO Role
(RoleName)
VALUES
('Administrator'),
('JMO'),
('Doctor'),
('Lab Technician'),
('Evidence Officer');

-- ==========================================
-- Permission
-- ==========================================
INSERT INTO Permission
(PermissionName)
VALUES
('Manage Users'),
('Manage Cases'),
('View Reports'),
('Manage Evidence'),
('Perform Laboratory Tests'),
('Generate Court Reports');

-- ==========================================
-- RolePermission
-- ==========================================
INSERT INTO RolePermission
(RoleID, PermissionID)
VALUES
(1,1),
(1,2),
(1,3),
(1,4),
(1,5),
(1,6),
(2,2),
(2,3),
(2,6),
(3,2),
(3,3),
(4,5),
(5,4);

-- ==========================================
-- AuditLog
-- ==========================================
INSERT INTO AuditLog
(UserID, Action, ActionDate)
VALUES
(1,'Logged into the system','2026-01-10 08:30:00'),
(2,'Created postmortem report','2026-01-13 10:15:00'),
(3,'Updated patient record','2026-01-18 11:45:00'),
(4,'Completed laboratory test','2026-03-12 14:20:00'),
(5,'Collected evidence','2026-01-12 09:00:00');

-- ==========================================
-- Notification
-- ==========================================
INSERT INTO Notification
(UserID, Message, CreatedDate, Status)
VALUES
(1,'New user account created.','2026-01-10 09:00:00','Unread'),
(2,'Postmortem examination assigned.','2026-01-12 08:30:00','Read'),
(3,'Patient case updated.','2026-01-18 12:00:00','Unread'),
(4,'Laboratory test assigned.','2026-03-10 10:00:00','Unread'),
(5,'Evidence transfer recorded.','2026-01-13 09:30:00','Read');

-- ==========================================
-- DigitalSignature
-- ==========================================
INSERT INTO DigitalSignature
(ReportID, SignedBy, SignatureData, SignedDate)
VALUES
(1,1,'DigitalSignatureHash001','2026-01-20'),
(3,2,'DigitalSignatureHash002','2026-02-10'),
(5,1,'DigitalSignatureHash003','2026-03-15');

-- ==========================================
-- BackupRecord
-- ==========================================
INSERT INTO BackupRecord
(BackupDate, Location, Status)
VALUES
('2026-01-31 23:59:00','D:\\Backups\\January\\','Completed'),
('2026-02-28 23:59:00','D:\\Backups\\February\\','Completed'),
('2026-03-31 23:59:00','D:\\Backups\\March\\','Completed'),
('2026-04-30 23:59:00','D:\\Backups\\April\\','Completed'),
('2026-05-31 23:59:00','D:\\Backups\\May\\','Completed');