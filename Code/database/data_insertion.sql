USE ForensicMedicalDB;

-- =========================================================
-- FK-SAFE DATA INSERTION SCRIPT
-- Insert parent tables before child tables.
-- Explicit IDs are used so all foreign-key references remain valid.
-- Run this on a freshly created/empty ForensicMedicalDB database.
-- =========================================================

-- =========================================================
-- 1. UserAccount
-- =========================================================
INSERT INTO UserAccount
(UserID, Username, Password, UserRole, StaffID)
VALUES
(1,'admin','admin123','IT Administrator',5),
(2,'jmo1','jmo123','JMO',1),
(3,'doctor2','doctor123','Doctor',2),
(4,'labtech','lab123','Laboratory Assistant',3),
(5,'evidence1','evidence123','Field Duty Officer',4);

-- =========================================================
-- 2. AuditLog
-- =========================================================
INSERT INTO AuditLog
(AuditID, UserID, Action, ActionDate)
VALUES
(1,1,'Logged into the system','2026-01-10 08:30:00'),
(2,2,'Created postmortem report','2026-01-13 10:15:00'),
(3,3,'Updated patient record','2026-01-18 11:45:00'),
(4,4,'Completed laboratory test','2026-03-12 14:20:00'),
(5,5,'Collected evidence','2026-01-12 09:00:00');

-- =========================================================
-- 3. Patient
-- =========================================================
INSERT INTO Patient
(PatientID, FullName, NIC, DateOfBirth, Gender, Address, ContactNo, RegistrationDate)
VALUES
(1,'Nimal Perera','901234567V','1990-05-12','Male','Colombo','0711111111','2026-01-10'),
(2,'Kumari Silva','921234568V','1992-08-20','Female','Kandy','0722222222','2026-01-15'),
(3,'Sunil Fernando','851234569V','1985-02-18','Male','Galle','0773333333','2026-02-01'),
(4,'Anjali Jayasinghe','951234570V','1995-11-10','Female','Kurunegala','0764444444','2026-02-12'),
(5,'Kasun Wijesinghe','881234571V','1988-04-30','Male','Negombo','0755555555','2026-03-05');

-- =========================================================
-- 4. PatientHistory
-- =========================================================
INSERT INTO PatientHistory
(HistoryID, PatientID, MedicalHistory, PreviousCases)
VALUES
(1,1,'No chronic illness','None'),
(2,2,'Asthma','Minor assault case'),
(3,3,'Diabetes','Traffic accident'),
(4,4,'Healthy','None'),
(5,5,'Hypertension','Domestic violence investigation');

-- =========================================================
-- 5. Staff
-- =========================================================
INSERT INTO Staff
(StaffID, StaffName, Role, ContactNo, Email)
VALUES
(1,'Dr. Samantha Perera','Doctor','0719000001','sam@fmh.lk'),
(2,'Dr. Nadeesha Silva','Doctor','0719000002','nadeesha@fmh.lk'),
(3,'Kasun Gunawardena','Laboratory Assistant','0719000003','kasun@fmh.lk'),
(4,'Ruwan Fernando','Field Duty Officer','0719000004','ruwan@fmh.lk'),
(5,'Nimali Jayawardena','IT Administrator','0719000005','nimali@fmh.lk');

-- =========================================================
-- 6. Doctor
-- FK: StaffID -> Staff(StaffID)
-- =========================================================
INSERT INTO Doctor
(DoctorID, StaffID, Specialization, LicenseNo)
VALUES
(1,1,'Forensic Medicine','SLMC1001'),
(2,2,'Pathology','SLMC1002');

-- =========================================================
-- 7. JMO
-- FK: DoctorID -> Doctor(DoctorID)
-- =========================================================
INSERT INTO JMO
(JMO_ID, DoctorID, Department)
VALUES
(1,1,'Judicial Medical Unit'),
(2,2,'Forensic Pathology Unit');

-- =========================================================
-- 8. Laboratory
-- =========================================================
INSERT INTO Laboratory
(LabID, LabName, Location)
VALUES
(1,'Central Forensic Laboratory','Colombo'),
(2,'DNA Analysis Laboratory','Kandy'),
(3,'Toxicology Laboratory','Galle');

-- =========================================================
-- 9. ForensicCase
-- FK: PatientID -> Patient(PatientID)
-- =========================================================
INSERT INTO ForensicCase
(CaseID, PatientID, CaseNumber, CaseType, IncidentDate, IncidentLocation, CaseDescription, Status)
VALUES
(1,1,'FC001','Homicide','2026-01-12','Colombo','Suspected homicide investigation','Open'),
(2,2,'FC002','Assault','2026-01-18','Kandy','Physical assault case','Under Investigation'),
(3,3,'FC003','Traffic Accident','2026-02-05','Galle','Fatal road accident','Closed'),
(4,4,'FC004','Suicide','2026-02-15','Kurunegala','Suspected suicide','Open'),
(5,5,'FC005','Poisoning','2026-03-10','Negombo','Poisoning investigation','Pending');

-- =========================================================
-- 10. Incident
-- FK: CaseID -> ForensicCase(CaseID)
-- =========================================================
INSERT INTO Incident
(IncidentID, CaseID, IncidentType, PoliceStation, Description)
VALUES
(1,1,'Murder','Colombo Central Police','Victim found in residence'),
(2,2,'Assault','Kandy Police','Fight reported'),
(3,3,'Road Accident','Galle Police','Collision involving two vehicles'),
(4,4,'Suicide','Kurunegala Police','Body recovered at home'),
(5,5,'Poisoning','Negombo Police','Possible toxic substance');

-- =========================================================
-- 11. Postmortem
-- =========================================================
INSERT INTO Postmortem
(PostmortemID, CaseID, JMO_ID, ExaminationDate, Findings, CauseOfDeath)
VALUES
(1,1,1,'2026-01-13','Multiple stab wounds','Hemorrhagic shock'),
(2,3,2,'2026-02-06','Severe head injuries','Head trauma'),
(3,4,1,'2026-02-16','Ligature mark present','Asphyxia'),
(4,5,2,'2026-03-11','Poison detected','Chemical poisoning');

-- =========================================================
-- 12. ExaminationReport
-- =========================================================
INSERT INTO ExaminationReport
(ReportID, PostmortemID, ReportDetails, CreatedDate)
VALUES
(1,1,'Complete postmortem report submitted.','2026-01-14'),
(2,2,'Traffic accident findings recorded.','2026-02-07'),
(3,3,'Suicide examination completed.','2026-02-17'),
(4,4,'Toxicology report attached.','2026-03-12');

-- =========================================================
-- 13. Evidence
-- =========================================================
INSERT INTO Evidence
(EvidenceID, CaseID, EvidenceType, Description, StorageLocation, CollectedDate)
VALUES
(1,1,'Knife','Blood stained knife','Locker A1','2026-01-12'),
(2,1,'Clothing','Victim clothing','Locker A2','2026-01-12'),
(3,2,'Photographs','Crime scene photos','Digital Archive','2026-01-18'),
(4,3,'Vehicle Parts','Broken bumper','Warehouse B','2026-02-05'),
(5,5,'Blood Sample','Victim blood sample','Cold Storage','2026-03-10');

-- =========================================================
-- 14. EvidenceSample
-- =========================================================
INSERT INTO EvidenceSample
(SampleID, EvidenceID, SampleType, SampleStatus)
VALUES
(1,1,'Blood','Received'),
(2,2,'Fabric','Stored'),
(3,3,'Digital','Verified'),
(4,4,'Metal','Testing'),
(5,5,'Blood','Testing');

-- =========================================================
-- 15. ChainOfCustody
-- =========================================================
INSERT INTO ChainOfCustody
(CustodyID, EvidenceID, StaffID, TransferDate, ActionTaken)
VALUES
(1,1,4,'2026-01-12','Collected'),
(2,2,4,'2026-01-13','Transferred to storage'),
(3,3,5,'2026-01-18','Archived'),
(4,4,4,'2026-02-05','Sent for examination'),
(5,5,3,'2026-03-10','Delivered to laboratory');

-- =========================================================
-- 16. LaboratoryTest
-- =========================================================
INSERT INTO LaboratoryTest
(TestID, EvidenceID, LabID, TestType, Result, TestDate)
VALUES
(1,1,1,'DNA Analysis','DNA matched suspect','2026-01-15'),
(2,2,1,'Fiber Analysis','Fibers identified','2026-01-16'),
(3,4,2,'Material Analysis','Vehicle paint matched','2026-02-07'),
(4,5,3,'Toxicology','Poison detected','2026-03-12');

-- =========================================================
-- 17. Court
-- =========================================================
INSERT INTO Court
(CourtID, CourtName, Location)
VALUES
(1,'Colombo High Court','Colombo'),
(2,'Kandy High Court','Kandy'),
(3,'Galle High Court','Galle');

-- =========================================================
-- 18. CourtReport
-- =========================================================
INSERT INTO CourtReport
(CourtReportID, CaseID, SubmissionDate, Status, ReportContent)
VALUES
(1,1,'2026-01-20','Submitted','Final forensic report submitted to Colombo High Court.'),
(2,2,'2026-01-25','Pending','Assault investigation report awaiting approval.'),
(3,3,'2026-02-10','Submitted','Traffic accident forensic report submitted.'),
(4,4,'2026-02-20','Draft','Suicide investigation report under review.'),
(5,5,'2026-03-15','Submitted','Poisoning investigation report submitted.');

-- =========================================================
-- 19. CaseCourt
-- =========================================================
INSERT INTO CaseCourt
(CaseCourtID, CaseID, CourtID, HearingDate)
VALUES
(1,1,1,'2026-02-05'),
(2,2,2,'2026-02-10'),
(3,3,3,'2026-02-25'),
(4,4,2,'2026-03-05'),
(5,5,1,'2026-03-25');

-- =========================================================
-- 20. Role
-- =========================================================
INSERT INTO Role
(RoleID, RoleName)
VALUES
(1,'IT Administrator'),
(2,'JMO'),
(3,'Doctor'),
(4,'Lab Assistant'),
(5,'F Officer');

-- =========================================================
-- 21. Permission
-- =========================================================
INSERT INTO Permission
(PermissionID, PermissionName)
VALUES
(1,'Manage Users'),
(2,'Manage Cases'),
(3,'View Reports'),
(4,'Manage Evidence'),
(5,'Perform Laboratory Tests'),
(6,'Generate Court Reports');

-- =========================================================
-- 22. RolePermission
-- =========================================================
INSERT INTO RolePermission
(RolePermissionID, RoleID, PermissionID)
VALUES
(1,1,1),
(2,1,2),
(3,1,3),
(4,1,4),
(5,1,5),
(6,1,6),
(7,2,2),
(8,2,3),
(9,2,6),
(10,3,2),
(11,3,3),
(12,4,5),
(13,5,4);

-- =========================================================
-- 23. Notification
-- =========================================================
INSERT INTO Notification
(UserID, Message, CreatedDate, Status)
VALUES
(1,'New user account created.','2026-01-10 09:00:00','Unread'),
(2,'Postmortem examination assigned.','2026-01-12 08:30:00','Read'),
(3,'Patient case updated.','2026-01-18 12:00:00','Unread'),
(4,'Laboratory test assigned.','2026-03-10 10:00:00','Unread'),
(5,'Evidence transfer recorded.','2026-01-13 09:30:00','Read');

-- =========================================================
-- 24. DigitalSignature
-- =========================================================
INSERT INTO DigitalSignature
(SignatureID, ReportID, SignedBy, SignatureData, SignedDate)
VALUES
(1,1,1,'DigitalSignatureHash001','2026-01-20'),
(2,3,2,'DigitalSignatureHash002','2026-02-10'),
(3,5,1,'DigitalSignatureHash003','2026-03-15');

-- =========================================================
-- 25. BackupRecord
-- =========================================================
INSERT INTO BackupRecord
(BackupID, BackupDate, Location, Status)
VALUES
(1,'2026-01-31 23:59:00','D:\\Backups\\January\\','Completed'),
(2,'2026-02-28 23:59:00','D:\\Backups\\February\\','Completed'),
(3,'2026-03-31 23:59:00','D:\\Backups\\March\\','Completed'),
(4,'2026-04-30 23:59:00','D:\\Backups\\April\\','Completed'),
(5,'2026-05-31 23:59:00','D:\\Backups\\May\\','Completed');

