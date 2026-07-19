from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Load dotenv relative to this file
load_dotenv(Path(__file__).resolve().parent / ".env")

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ForensicMedicalDB'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306))
}

print("=" * 60)
print("Starting Forensa Application")
print("=" * 60)
print(f"Database: {DB_CONFIG['database']}")
print(f"User: {DB_CONFIG['user']}")
print(f"Host: {DB_CONFIG['host']}")
print("=" * 60)

# ==========================================
# Database Helper Functions
# ==========================================

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def execute_query(query: str, params: tuple | None = None, fetch: bool = True):
    """Execute a query and return results with proper error handling"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Execute the query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Handle SELECT queries
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
            # Consume any remaining results
            while cursor.nextset():
                pass
        else:
            connection.commit()
            result = cursor.lastrowid if query.strip().upper().startswith('INSERT') else None
        
        cursor.close()
        connection.close()
        return result
        
    except Error as e:
        print(f"Error executing query: {e}")
        print(f"Query: {query[:200]}...")
        if params:
            print(f"Params: {params}")
        if connection:
            connection.rollback()
            connection.close()
        return None

def add_audit(action: str, resource: str, username: str = "system_user") -> None:
    """Add an audit log entry to database"""
    try:
        # Query to get user_id from username
        user_query = "SELECT UserID FROM UserAccount WHERE Username = %s"
        user_result = execute_query(user_query, (username,))
        
        user_id = user_result[0]["UserID"] if user_result else 1
        
        insert_query = """
            INSERT INTO AuditLog (UserID, Action, ActionDate)
            VALUES (%s, %s, %s)
        """
        
        full_action = f"{action}: {resource}"
        current_time = datetime.now()
        
        execute_query(insert_query, (user_id, full_action, current_time), fetch=False)
    except Exception as e:
        print(f"Error adding audit log: {e}")

# ==========================================
# Database Initialization
# ==========================================

def init_database():
    """Initialize database and add sample data if needed"""
    try:
        connection = get_db_connection()
        if not connection:
            print("Could not connect to MySQL. Please check your credentials.")
            return
        
        # Check if the tables exist
        check_query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'ForensicCase'
        """
        result = execute_query(check_query, (DB_CONFIG['database'],))
        
        if not result or result[0]["count"] == 0:
            print("=" * 60)
            print("TABLES NOT FOUND!")
            print("=" * 60)
            print(f"Please create the tables in database: {DB_CONFIG['database']}")
            print("Run your SQL script to create all tables.")
            print("=" * 60)
            return
        
        print("Tables found in database.")
        
        # Check if we need to add sample data
        check_cases = "SELECT COUNT(*) as count FROM ForensicCase"
        count = execute_query(check_cases)
        
        if count and count[0]["count"] == 0:
            print("Adding sample data...")
            
            # Add sample staff
            staff_data = [
                ("Dr. R. Gunawardena", "Senior Pathologist", "011-2345678", "dr.gunawardena@forensic.lk"),
                ("Dr. K. Silva", "Laboratory Lead", "011-2345679", "dr.silva@forensic.lk"),
                ("Officer Fernando", "Field Duty Officer", "011-2345680", "officer.fernando@forensic.lk")
            ]
            
            for name, role, contact, email in staff_data:
                insert_staff = """
                    INSERT INTO Staff (StaffName, Role, ContactNo, Email)
                    VALUES (%s, %s, %s, %s)
                """
                execute_query(insert_staff, (name, role, contact, email), fetch=False)
            
            # Add sample cases
            cases_data = [
                ("FC-2026-001", "Homicide", "2026-07-10", "Forensic evaluation requested by law enforcement.", "Active"),
                ("PM-2026-884", "Post Mortem", "2026-07-15", "Post-mortem examination and documentation in progress.", "In Progress"),
                ("CC-2026-4022", "Court Testimony", "2026-07-02", "Expert testimony scheduled for Case Court 3.", "Scheduled")
            ]
            
            for case_num, case_type, date, desc, status in cases_data:
                insert_case = """
                    INSERT INTO ForensicCase (CaseNumber, CaseType, IncidentDate, CaseDescription, Status)
                    VALUES (%s, %s, %s, %s, %s)
                """
                execute_query(insert_case, (case_num, case_type, date, desc, status), fetch=False)
            
            # Add sample laboratory tests
            lab_data = [
                ("Blood / Toxicology", "Toxicology screening underway.", "2026-07-17"),
                ("DNA Specimen", "DNA profile completed.", "2026-07-16")
            ]
            
            for test_type, result, date in lab_data:
                insert_lab = """
                    INSERT INTO LaboratoryTest (TestType, Result, TestDate)
                    VALUES (%s, %s, %s)
                """
                execute_query(insert_lab, (test_type, result, date), fetch=False)
            
        # Ensure Lab Technician has 'Manage Evidence' permission (RoleID 4, PermissionID 4)
        check_lp = "SELECT RolePermissionID FROM RolePermission WHERE RoleID = 4 AND PermissionID = 4"
        if not execute_query(check_lp):
            insert_lp = "INSERT INTO RolePermission (RoleID, PermissionID) VALUES (4, 4)"
            execute_query(insert_lp, fetch=False)

        print("Database initialization complete!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

# ==========================================
# Lifespan Event
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Forensa application...")
    init_database()
    yield
    # Shutdown
    print("Shutting down application...")

# ==========================================
# FastAPI App Initialization
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="Forensa API (MySQL Database)", 
    version="2.0.0", 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Pydantic Models
# ==========================================

class UserSignup(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    role: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class CaseCreate(BaseModel):
    case_number: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    case_type: str
    status: str
    assigned_to: str | None = None
    opened_date: str
    description: str = ""

class CaseUpdate(BaseModel):
    title: str | None = None
    case_type: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    opened_date: str | None = None
    description: str | None = None

class IncidentCreate(BaseModel):
    case_id: int
    incident_type: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=200)
    police_station: str = Field(min_length=2, max_length=100)
    description: str = ""
    incident_date: str

# ==========================================
# Resource Mapping
# ==========================================

RESOURCES = {"laboratory", "court-reports", "incidents", "staff", "audit-logs"}
resource_mapping = {
    "laboratory": "LaboratoryTest",
    "court-reports": "CourtReport",
    "incidents": "Incident",
    "staff": "Staff",
    "audit-logs": "AuditLog"
}

# ==========================================
# Role Mapping Configuration
# ==========================================

ROLE_MAP = {
    "Senior Pathologist": "JMO",
    "Laboratory Lead": "Lab Technician",
    "Laboratory Assistant": "Lab Technician",
    "Field Duty Officer": "Evidence Officer",
    "Medical Observer": "Doctor",
    "IT Administrator": "Administrator"
}

# ==========================================
# Authentication Dependency
# ==========================================

def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    token = authorization.split(" ")[1]
    if not token.startswith("mock-token-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    username = token.replace("mock-token-", "", 1)
    
    # Query database for user
    user_query = """
        SELECT u.Username, s.StaffName, u.UserRole 
        FROM UserAccount u 
        LEFT JOIN Staff s ON u.StaffID = s.StaffID 
        WHERE u.Username = %s
    """
    result = execute_query(user_query, (username,))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session not found"
        )
    user_row = result[0]
    return {
        "username": user_row["Username"],
        "full_name": user_row["StaffName"] or user_row["Username"],
        "role": user_row["UserRole"]
    }

# ==========================================
# Permission Helper
# ==========================================

def check_permission(username: str, permission_name: str) -> bool:
    """Check if a user's role has the specified permission in the database"""
    query = """
        SELECT COUNT(*) as count 
        FROM UserAccount u
        JOIN Role r ON u.UserRole = r.RoleName
        JOIN RolePermission rp ON r.RoleID = rp.RoleID
        JOIN Permission p ON rp.PermissionID = p.PermissionID
        WHERE u.Username = %s AND p.PermissionName = %s
    """
    result = execute_query(query, (username, permission_name))
    return result and result[0]["count"] > 0

# ==========================================
# Helper Functions
# ==========================================

def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))

def page_heading(title: str, body: str) -> str:
    return f'<h2 style="color:#260099;border-bottom:2px solid #260099;margin-top:0;padding-bottom:5px;font-size:18px;">{esc(title)}</h2>{body}'

def find_case(case_id: int) -> dict[str, Any]:
    query = """
        SELECT fc.*, s.StaffName as AssignedStaff 
        FROM ForensicCase fc 
        LEFT JOIN Postmortem pm ON fc.CaseID = pm.CaseID 
        LEFT JOIN JMO j ON pm.JMO_ID = j.JMO_ID 
        LEFT JOIN Doctor d ON j.DoctorID = d.DoctorID 
        LEFT JOIN Staff s ON d.StaffID = s.StaffID
        WHERE fc.CaseID = %s
    """
    result = execute_query(query, (case_id,))
    if not result:
        raise HTTPException(404, "Case not found")
    row = result[0]
    
    desc = row['CaseDescription'] or ""
    if " -- " in desc:
        title, description = desc.split(" -- ", 1)
    else:
        title = desc
        description = ""
        
    return {
        "id": row["CaseID"],
        "case_number": row["CaseNumber"],
        "title": title,
        "case_type": row["CaseType"],
        "status": row["Status"],
        "assigned_to": row["AssignedStaff"],
        "opened_date": str(row["IncidentDate"]) if row["IncidentDate"] else "",
        "description": description
    }

# ==========================================
# Auth Endpoints
# ==========================================

@app.post("/api/auth/signup")
def signup(payload: UserSignup) -> dict[str, Any]:
    username_lower = payload.username.strip().lower()
    if not username_lower:
        raise HTTPException(400, "Username cannot be empty")
    
    # Check if user already exists
    check_user = "SELECT UserID FROM UserAccount WHERE Username = %s"
    if execute_query(check_user, (username_lower,)):
        raise HTTPException(400, "Username already exists")
    
    # Insert into Staff table first (retaining the friendly role name for staff lists)
    insert_staff = """
        INSERT INTO Staff (StaffName, Role, ContactNo, Email)
        VALUES (%s, %s, 'N/A', 'N/A')
    """
    staff_id = execute_query(insert_staff, (payload.full_name.strip(), payload.role.strip()), fetch=False)
    
    # Map friendly role to database group role for permissions
    db_role = ROLE_MAP.get(payload.role.strip(), payload.role.strip())
    
    # Insert into UserAccount table
    insert_user = """
        INSERT INTO UserAccount (Username, Password, UserRole, StaffID)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(insert_user, (username_lower, payload.password, db_role, staff_id), fetch=False)
    
    # If the role is JMO/Doctor compatible, register in the Doctor and JMO tables
    if payload.role.strip() in {"Senior Pathologist", "Medical Observer"}:
        # Insert into Doctor
        spec = "Pathology" if payload.role.strip() == "Senior Pathologist" else "Forensic Medicine"
        license_no = f"SLMC-{datetime.now().strftime('%M%S')}"
        insert_doc = """
            INSERT INTO Doctor (StaffID, Specialization, LicenseNo)
            VALUES (%s, %s, %s)
        """
        doc_id = execute_query(insert_doc, (staff_id, spec, license_no), fetch=False)
        
        # Insert into JMO
        dept = "Forensic Pathology Unit" if payload.role.strip() == "Senior Pathologist" else "Judicial Medical Unit"
        insert_jmo = """
            INSERT INTO JMO (DoctorID, Department)
            VALUES (%s, %s)
        """
        execute_query(insert_jmo, (doc_id, dept), fetch=False)
        
    add_audit("Signed Up User", username_lower, username_lower)
    return {"username": username_lower, "full_name": payload.full_name, "role": payload.role}

@app.post("/api/auth/login")
def login(payload: UserLogin) -> dict[str, Any]:
    username_lower = payload.username.strip().lower()
    
    # Query database for user
    user_query = """
        SELECT u.Username, u.Password, s.StaffName, u.UserRole 
        FROM UserAccount u 
        LEFT JOIN Staff s ON u.StaffID = s.StaffID 
        WHERE u.Username = %s
    """
    result = execute_query(user_query, (username_lower,))
    if not result or result[0]["Password"] != payload.password:
        raise HTTPException(401, "Invalid username or password")
    
    user = result[0]
    token = f"mock-token-{username_lower}"
    add_audit("Logged In", username_lower, username_lower)
    return {
        "token": token,
        "username": username_lower,
        "full_name": user["StaffName"] or user["Username"],
        "role": user["UserRole"]
    }

# ==========================================
# Cases API Endpoints
# ==========================================

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": "database", "database": "connected"}

@app.get("/api/cases")
def list_cases(status_filter: str | None = None, authorization: str | None = Header(None)) -> list[dict[str, Any]]:
    get_current_user(authorization)
    
    if status_filter:
        query = """
            SELECT fc.*, s.StaffName as AssignedStaff 
            FROM ForensicCase fc 
            LEFT JOIN Postmortem pm ON fc.CaseID = pm.CaseID 
            LEFT JOIN JMO j ON pm.JMO_ID = j.JMO_ID 
            LEFT JOIN Doctor d ON j.DoctorID = d.DoctorID 
            LEFT JOIN Staff s ON d.StaffID = s.StaffID
            WHERE fc.Status = %s
        """
        result = execute_query(query, (status_filter,))
    else:
        query = """
            SELECT fc.*, s.StaffName as AssignedStaff 
            FROM ForensicCase fc 
            LEFT JOIN Postmortem pm ON fc.CaseID = pm.CaseID 
            LEFT JOIN JMO j ON pm.JMO_ID = j.JMO_ID 
            LEFT JOIN Doctor d ON j.DoctorID = d.DoctorID 
            LEFT JOIN Staff s ON d.StaffID = s.StaffID
        """
        result = execute_query(query)
        
    cases_list = []
    for row in (result or []):
        desc = row['CaseDescription'] or ""
        if " -- " in desc:
            title, description = desc.split(" -- ", 1)
        else:
            title = desc
            description = ""
            
        cases_list.append({
            "id": row["CaseID"],
            "case_number": row["CaseNumber"],
            "title": title,
            "case_type": row["CaseType"],
            "status": row["Status"],
            "assigned_to": row["AssignedStaff"],
            "opened_date": str(row["IncidentDate"]) if row["IncidentDate"] else "",
            "description": description
        })
        
    return sorted(cases_list, key=lambda item: item["id"], reverse=True)

@app.get("/api/cases/{case_id}")
def get_case(case_id: int, authorization: str | None = Header(None)) -> dict[str, Any]:
    get_current_user(authorization)
    return find_case(case_id)

@app.post("/api/cases", status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    
    # Check permission
    if not check_permission(user["username"], "Manage Cases"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Your role does not have permission to manage cases."
        )
    
    # Check if case_number already exists
    check_query = "SELECT CaseID FROM ForensicCase WHERE CaseNumber = %s"
    if execute_query(check_query, (payload.case_number,)):
        raise HTTPException(409, "Case number already exists")
    
    # Combine title and description
    combined_desc = f"{payload.title} -- {payload.description}"
    
    # Insert case
    insert_query = """
        INSERT INTO ForensicCase (CaseNumber, CaseType, IncidentDate, CaseDescription, Status)
        VALUES (%s, %s, %s, %s, %s)
    """
    case_id = execute_query(insert_query, (payload.case_number, payload.case_type, payload.opened_date, combined_desc, payload.status), fetch=False)
    
    # Handle assignment if assigned_to is specified
    if payload.assigned_to:
        jmo_query = """
            SELECT j.JMO_ID 
            FROM JMO j 
            JOIN Doctor d ON j.DoctorID = d.DoctorID 
            JOIN Staff s ON d.StaffID = s.StaffID 
            WHERE s.StaffName = %s
        """
        jmo_result = execute_query(jmo_query, (payload.assigned_to,))
        if jmo_result:
            jmo_id = jmo_result[0]["JMO_ID"]
            insert_pm = """
                INSERT INTO Postmortem (CaseID, JMO_ID, ExaminationDate, Findings, CauseOfDeath)
                VALUES (%s, %s, %s, 'Pending examination', 'Pending')
            """
            execute_query(insert_pm, (case_id, jmo_id, payload.opened_date), fetch=False)
            
    add_audit("Created Case", payload.case_number, user["username"])
    return find_case(case_id)

@app.patch("/api/cases/{case_id}")
def update_case(case_id: int, payload: CaseUpdate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    
    # Check permission
    if not check_permission(user["username"], "Manage Cases"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Your role does not have permission to manage cases."
        )
    
    # Fetch existing case
    existing = find_case(case_id)
    
    # Prepare updated values
    title = payload.title if payload.title is not None else existing["title"]
    description = payload.description if payload.description is not None else existing["description"]
    combined_desc = f"{title} -- {description}"
    
    case_type = payload.case_type if payload.case_type is not None else existing["case_type"]
    status_val = payload.status if payload.status is not None else existing["status"]
    opened_date = payload.opened_date if payload.opened_date is not None else existing["opened_date"]
    
    # Update ForensicCase
    update_query = """
        UPDATE ForensicCase 
        SET CaseType = %s, Status = %s, IncidentDate = %s, CaseDescription = %s
        WHERE CaseID = %s
    """
    execute_query(update_query, (case_type, status_val, opened_date, combined_desc, case_id), fetch=False)
    
    # Handle assignment update
    if payload.assigned_to is not None:
        execute_query("DELETE FROM Postmortem WHERE CaseID = %s", (case_id,), fetch=False)
        
        if payload.assigned_to:
            jmo_query = """
                SELECT j.JMO_ID 
                FROM JMO j 
                JOIN Doctor d ON j.DoctorID = d.DoctorID 
                JOIN Staff s ON d.StaffID = s.StaffID 
                WHERE s.StaffName = %s
            """
            jmo_result = execute_query(jmo_query, (payload.assigned_to,))
            if jmo_result:
                jmo_id = jmo_result[0]["JMO_ID"]
                insert_pm = """
                    INSERT INTO Postmortem (CaseID, JMO_ID, ExaminationDate, Findings, CauseOfDeath)
                    VALUES (%s, %s, %s, 'Pending examination', 'Pending')
                """
                execute_query(insert_pm, (case_id, jmo_id, opened_date), fetch=False)
                
    add_audit("Updated Case", existing["case_number"], user["username"])
    return find_case(case_id)

@app.delete("/api/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int, authorization: str | None = Header(None)) -> Response:
    user = get_current_user(authorization)
    
    # Check permission
    if not check_permission(user["username"], "Manage Cases"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Your role does not have permission to manage cases."
        )
        
    existing = find_case(case_id)
    
    # Cascade delete to satisfy foreign key constraints:
    
    # 1. Delete from ExaminationReport
    delete_exam = """
        DELETE FROM ExaminationReport 
        WHERE PostmortemID IN (SELECT PostmortemID FROM Postmortem WHERE CaseID = %s)
    """
    execute_query(delete_exam, (case_id,), fetch=False)
    
    # 2. Delete from Postmortem
    execute_query("DELETE FROM Postmortem WHERE CaseID = %s", (case_id,), fetch=False)
    
    # 3. Delete from Incident
    execute_query("DELETE FROM Incident WHERE CaseID = %s", (case_id,), fetch=False)
    
    # 4. Delete from CourtReport
    execute_query("DELETE FROM CourtReport WHERE CaseID = %s", (case_id,), fetch=False)
    
    # 5. Delete from CaseCourt
    execute_query("DELETE FROM CaseCourt WHERE CaseID = %s", (case_id,), fetch=False)
    
    # 6. Delete from dependent Evidence tables
    evidence_ids_query = "SELECT EvidenceID FROM Evidence WHERE CaseID = %s"
    evidence_rows = execute_query(evidence_ids_query, (case_id,)) or []
    evidence_ids = [row["EvidenceID"] for row in evidence_rows]
    
    if evidence_ids:
        placeholders = ", ".join(["%s"] * len(evidence_ids))
        execute_query(f"DELETE FROM EvidenceSample WHERE EvidenceID IN ({placeholders})", tuple(evidence_ids), fetch=False)
        execute_query(f"DELETE FROM ChainOfCustody WHERE EvidenceID IN ({placeholders})", tuple(evidence_ids), fetch=False)
        execute_query(f"DELETE FROM LaboratoryTest WHERE EvidenceID IN ({placeholders})", tuple(evidence_ids), fetch=False)
        
    # 7. Delete from Evidence
    execute_query("DELETE FROM Evidence WHERE CaseID = %s", (case_id,), fetch=False)
    
    # 8. Delete from ForensicCase
    execute_query("DELETE FROM ForensicCase WHERE CaseID = %s", (case_id,), fetch=False)
    
    add_audit("Deleted Case", existing["case_number"], user["username"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    
    # Check permission
    if not check_permission(user["username"], "Manage Evidence"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Your role does not have permission to manage incidents/evidence."
        )
        
    # Check if case exists
    case_query = "SELECT CaseID FROM ForensicCase WHERE CaseID = %s"
    if not execute_query(case_query, (payload.case_id,)):
        raise HTTPException(404, "Case not found")
        
    # Update ForensicCase location
    update_case = "UPDATE ForensicCase SET IncidentLocation = %s WHERE CaseID = %s"
    execute_query(update_case, (payload.location, payload.case_id), fetch=False)
    
    # Insert incident (excluding location as it resides in ForensicCase)
    insert_query = """
        INSERT INTO Incident (CaseID, IncidentType, PoliceStation, Description, IncidentDate)
        VALUES (%s, %s, %s, %s, %s)
    """
    incident_id = execute_query(
        insert_query, 
        (payload.case_id, payload.incident_type, payload.police_station, payload.description, payload.incident_date), 
        fetch=False
    )
    
    add_audit("Created Incident", f"INC-{incident_id}", user["username"])
    
    return {
        "id": incident_id,
        "case_id": payload.case_id,
        "incident_type": payload.incident_type,
        "location": payload.location,
        "police_station": payload.police_station,
        "description": payload.description,
        "incident_date": payload.incident_date
    }

# ==========================================
# Generic Resource Endpoint
# ==========================================

resource_primary_keys = {
    "laboratory": "TestID",
    "court-reports": "CourtReportID",
    "incidents": "IncidentID",
    "staff": "StaffID",
    "audit-logs": "AuditID"
}

@app.get("/api/{resource_name}")
def list_resource(resource_name: str, authorization: str | None = Header(None)) -> list[dict[str, Any]]:
    user = get_current_user(authorization)
    if resource_name not in RESOURCES:
        raise HTTPException(404, "Resource not found")
        
    # Map resource to required permission
    resource_permissions = {
        "laboratory": "Perform Laboratory Tests",
        "court-reports": "Generate Court Reports",
        "incidents": "Manage Evidence",
        "staff": "View Reports",
        "audit-logs": "Manage Users"
    }
    
    if resource_name in resource_permissions:
        required_perm = resource_permissions[resource_name]
        if not check_permission(user["username"], required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied to access resource {resource_name}"
            )
    
    table_name = resource_mapping[resource_name]
    pk_column = resource_primary_keys[resource_name]
    query = f"SELECT * FROM {table_name} ORDER BY {pk_column} DESC"
    result = execute_query(query)
    if result is None:
        raise HTTPException(500, "Database error")
    
    formatted_result = []
    for row in result:
        if resource_name == "staff":
            formatted_result.append({
                "id": row.get("StaffID"),
                "employee_number": f"EMP-{row.get('StaffID')}",
                "full_name": row.get("StaffName") or "Unknown",
                "role": row.get("Role") or "Staff",
                "extension": "N/A",
                "duty_status": "On Duty",
                "shift": "Day"
            })
        elif resource_name == "laboratory":
            formatted_result.append({
                "id": row.get("TestID"),
                "request_number": f"LAB-{row.get('TestID')}",
                "sample_type": row.get("TestType") or "Unknown",
                "assigned_analyst": "Dr. K. Silva",
                "status": "Completed" if row.get("Result") else "In Progress",
                "received_date": str(row.get("TestDate")) if row.get("TestDate") else None,
                "notes": row.get("Result") or "No results yet"
            })
        elif resource_name == "court-reports":
            formatted_result.append({
                "id": row.get("CourtReportID"),
                "report_number": f"CR-{row.get('CourtReportID')}",
                "case_number": "FC-2026-001",
                "court_name": "High Court",
                "testimony_date": str(row.get("SubmissionDate")) if row.get("SubmissionDate") else None,
                "status": row.get("Status") or "Draft",
                "signed_by": "JMO Officer",
                "summary": row.get("ReportContent") or ""
            })
        elif resource_name == "incidents":
            formatted_result.append({
                "id": row.get("IncidentID"),
                "incident_number": f"INC-{row.get('IncidentID')}",
                "title": row.get("IncidentType") or "Incident",
                "location": row.get("PoliceStation") or "Unknown",
                "status": "Active"
            })
        elif resource_name == "audit-logs":
            formatted_result.append({
                "id": row.get("AuditID"),
                "timestamp": str(row.get("ActionDate")) if row.get("ActionDate") else None,
                "username": f"user-{row.get('UserID')}",
                "action": row.get("Action") or "Unknown Action",
                "resource": "System"
            })
    return formatted_result

# ==========================================
# Dynamic Pages Serving fragments
# ==========================================

@app.get("/api/pages/{page_id}", response_class=HTMLResponse)
def dynamic_page(page_id: str, authorization: str | None = Header(None)) -> str:
    if page_id in {"about_us", "contact_us", "login", "signup"}:
        return (FRONTEND_DIR / "pages" / f"{page_id}.html").read_text(encoding="utf-8")
    
    # Authenticate user for protected pages
    user = get_current_user(authorization)
    
    # Map page_id to required permission
    page_permissions = {
        "cases": "Manage Cases",
        "laboratory": "Perform Laboratory Tests",
        "court_reports": "Generate Court Reports",
        "incidents": "Manage Evidence",
        "staff": "View Reports",
        "audit_logs": "Manage Users"
    }
    
    if page_id in page_permissions:
        required_perm = page_permissions[page_id]
        if not check_permission(user["username"], required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied to access page {page_id}"
            )
    
    if page_id == "cases":
        can_manage = check_permission(user["username"], "Manage Cases")
        
        form_html = ""
        add_button = ""
        if can_manage:
            # Query JMOs for assignment dropdown
            jmo_list = execute_query("""
                SELECT DISTINCT s.StaffName 
                FROM JMO j 
                JOIN Doctor d ON j.DoctorID = d.DoctorID 
                JOIN Staff s ON d.StaffID = s.StaffID
                ORDER BY s.StaffName ASC
            """) or []
            
            jmo_options = "".join(f'<option value="{esc(row["StaffName"])}">{esc(row["StaffName"])}</option>' for row in jmo_list)
            
            add_button = (
                '<button onclick="toggleAddCaseForm()" style="background:#260099;color:white;border:0;padding:8px 20px;font-weight:bold;cursor:pointer;margin-bottom:15px;">'
                '+ Add New Case'
                '</button>'
            )
            
            form_html = f"""
            <div id="add-case-container" style="display:none;background:#f9f9fb;border:1px solid #c9c1b0;padding:20px;margin-bottom:15px;">
                <h3 style="margin-top:0;color:#260099;font-size:16px;">Add New Forensic Case</h3>
                <form onsubmit="handleCreateCase(event)" style="font-size:13px;">
                    <div style="margin-bottom:10px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Case Number:</label>
                        <input type="text" id="case-number" required placeholder="e.g. FC-2026-004" style="width:100%;padding:6px;border:1px solid #ccc;"/>
                    </div>
                    <div style="margin-bottom:10px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Title / Summary:</label>
                        <input type="text" id="case-title" required placeholder="e.g. Suspected poisoning investigation" style="width:100%;padding:6px;border:1px solid #ccc;"/>
                    </div>
                    <div style="display:flex;gap:10px;margin-bottom:10px;">
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Case Type:</label>
                            <select id="case-type" required style="width:100%;padding:6px;border:1px solid #ccc;">
                                <option value="Homicide">Homicide</option>
                                <option value="Post Mortem">Post Mortem</option>
                                <option value="Poisoning">Poisoning</option>
                                <option value="Assault">Assault</option>
                                <option value="Accident">Accident</option>
                            </select>
                        </div>
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Status:</label>
                            <select id="case-status" required style="width:100%;padding:6px;border:1px solid #ccc;">
                                <option value="Active">Active</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Pending">Pending</option>
                                <option value="Completed">Completed</option>
                            </select>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;margin-bottom:10px;">
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Date Opened:</label>
                            <input type="date" id="case-opened-date" required style="width:100%;padding:6px;border:1px solid #ccc;"/>
                        </div>
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Assigned JMO / Doctor:</label>
                            <select id="case-assigned-to" style="width:100%;padding:6px;border:1px solid #ccc;">
                                <option value="">Unassigned</option>
                                {jmo_options}
                            </select>
                        </div>
                    </div>
                    <div style="margin-bottom:15px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Description:</label>
                        <textarea id="case-description" rows="3" placeholder="Enter detailed case description..." style="width:100%;padding:6px;border:1px solid #ccc;"></textarea>
                    </div>
                    <button type="submit" style="background:#260099;color:white;border:0;padding:8px 20px;cursor:pointer;font-weight:bold;">Submit Case</button>
                    <button type="button" onclick="toggleAddCaseForm()" style="background:#e0dacb;color:#333;border:0;padding:8px 20px;cursor:pointer;margin-left:10px;">Cancel</button>
                </form>
            </div>
            """

        query = """
            SELECT fc.*, s.StaffName as AssignedStaff 
            FROM ForensicCase fc 
            LEFT JOIN Postmortem pm ON fc.CaseID = pm.CaseID 
            LEFT JOIN JMO j ON pm.JMO_ID = j.JMO_ID 
            LEFT JOIN Doctor d ON j.DoctorID = d.DoctorID 
            LEFT JOIN Staff s ON d.StaffID = s.StaffID
            ORDER BY fc.CaseID DESC LIMIT 20
        """
        cases = execute_query(query) or []
        
        cards = ""
        for row in cases:
            desc = row['CaseDescription'] or ""
            if " -- " in desc:
                title, description = desc.split(" -- ", 1)
            else:
                title = desc
                
            cards += (
                f'<div style="background:#fffdf5;border:1px solid #e0dacb;padding:15px;margin-bottom:8px;">'
                f'<strong>{esc(title)} – {esc(row["CaseNumber"])}</strong>'
                f'<p style="margin:8px 0;font-size:13px;">Status: {esc(row["Status"])} | Type: {esc(row["CaseType"])} | Assigned: {esc(row["AssignedStaff"] or "Unassigned")}</p>'
                f'<button onclick="showCase({row["CaseID"]})" style="background:#004488;color:white;border:0;padding:6px 15px;cursor:pointer;">View Case</button>'
                f'</div>'
            )
        return page_heading("Active Forensic Cases & Applications", f"{add_button}{form_html}{cards or '<p>No cases found.</p>'}")
    
    if page_id == "laboratory":
        query = "SELECT * FROM LaboratoryTest ORDER BY TestID DESC"
        tests = execute_query(query) or []
        
        body = "".join(f'<tr><td>LAB-{esc(str(row["TestID"]))}</td><td>{esc(row["TestType"])}</td><td>Analyst</td><td><strong>{esc("Completed" if row["Result"] else "In Progress")}</strong></td></tr>' for row in tests)
        return page_heading("Laboratory Services", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Request ID</th><th>Sample Type</th><th>Assigned Analyst</th><th>Status</th></tr>{body}</table>')
    
    if page_id == "court_reports":
        query = """
            SELECT cr.*, fc.CaseNumber 
            FROM CourtReport cr 
            LEFT JOIN ForensicCase fc ON cr.CaseID = fc.CaseID 
            ORDER BY cr.CourtReportID DESC
        """
        reports = execute_query(query) or []
        lis = "".join(f'<li><strong>CR-{esc(str(row["CourtReportID"]))} ({esc(row["CaseNumber"])}):</strong> {esc(row["Status"])} — {esc(row["ReportContent"])}</li>' for row in reports)
        return page_heading("Court Reports & Testimonies", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;"><ul>{lis}</ul></div>')
    
    if page_id == "incidents":
        can_manage = check_permission(user["username"], "Manage Evidence")
        
        form_html = ""
        add_button = ""
        if can_manage:
            # Query active cases for dropdown
            cases_list = execute_query("SELECT CaseID, CaseNumber FROM ForensicCase ORDER BY CaseID DESC") or []
            case_options = "".join(f'<option value="{row["CaseID"]}">{esc(row["CaseNumber"])}</option>' for row in cases_list)
            
            add_button = (
                '<button onclick="toggleAddIncidentForm()" style="background:#260099;color:white;border:0;padding:8px 20px;font-weight:bold;cursor:pointer;margin-bottom:15px;">'
                '+ Add New Incident'
                '</button>'
            )
            
            form_html = f"""
            <div id="add-incident-container" style="display:none;background:#f9f9fb;border:1px solid #c9c1b0;padding:20px;margin-bottom:15px;">
                <h3 style="margin-top:0;color:#260099;font-size:16px;">Add New Field Incident</h3>
                <form onsubmit="handleCreateIncident(event)" style="font-size:13px;">
                    <div style="margin-bottom:10px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Associate Case:</label>
                        <select id="incident-case-id" required style="width:100%;padding:6px;border:1px solid #ccc;">
                            {case_options}
                        </select>
                    </div>
                    <div style="margin-bottom:10px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Incident Type / Title:</label>
                        <input type="text" id="incident-type" required placeholder="e.g. Crime Scene Investigation" style="width:100%;padding:6px;border:1px solid #ccc;"/>
                    </div>
                    <div style="display:flex;gap:10px;margin-bottom:10px;">
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Incident Location:</label>
                            <input type="text" id="incident-location" required placeholder="e.g. Colombo 03" style="width:100%;padding:6px;border:1px solid #ccc;"/>
                        </div>
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Police Station:</label>
                            <input type="text" id="incident-police-station" required placeholder="e.g. Bambalapitiya" style="width:100%;padding:6px;border:1px solid #ccc;"/>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;margin-bottom:10px;">
                        <div style="flex:1;">
                            <label style="display:block;font-weight:bold;margin-bottom:3px;">Incident Date:</label>
                            <input type="date" id="incident-date" required style="width:100%;padding:6px;border:1px solid #ccc;"/>
                        </div>
                    </div>
                    <div style="margin-bottom:15px;">
                        <label style="display:block;font-weight:bold;margin-bottom:3px;">Description:</label>
                        <textarea id="incident-description" rows="3" placeholder="Enter detailed incident description..." style="width:100%;padding:6px;border:1px solid #ccc;"></textarea>
                    </div>
                    <button type="submit" style="background:#260099;color:white;border:0;padding:8px 20px;cursor:pointer;font-weight:bold;">Submit Incident</button>
                    <button type="button" onclick="toggleAddIncidentForm()" style="background:#e0dacb;color:#333;border:0;padding:8px 20px;cursor:pointer;margin-left:10px;">Cancel</button>
                </form>
            </div>
            """
            
        query = """
            SELECT i.*, fc.CaseNumber, fc.IncidentLocation 
            FROM Incident i 
            LEFT JOIN ForensicCase fc ON i.CaseID = fc.CaseID 
            ORDER BY i.IncidentID DESC
        """
        incidents = execute_query(query) or []
        content = "".join(f'<div style="margin-bottom:15px;"><strong>INC-{esc(str(row["IncidentID"]))}: {esc(row["IncidentType"])}</strong> ({esc(row["CaseNumber"])})<p style="margin:5px 0;font-size:13px;">Location: {esc(row["IncidentLocation"] or "Unknown")} | Police Station: {esc(row["PoliceStation"])}</p><p style="margin:5px 0;font-size:13px;font-style:italic;">{esc(row["Description"])}</p><hr style="border:0;border-top:1px solid #eee;"/></div>' for row in incidents) if incidents else "<p><em>No active field incident dispatches recorded.</em></p>"
        return page_heading("Incident Logs", f"{add_button}{form_html}<div style='background:white;border:1px solid #e0dacb;padding:20px;'>{content}</div>")
    
    if page_id == "staff":
        query = "SELECT * FROM Staff ORDER BY StaffID DESC"
        staff = execute_query(query) or []
        
        lis = "".join(f'<li><strong>{esc(row["Role"])}:</strong> {esc(row["StaffName"])} — {esc(row["ContactNo"])}</li>' for row in staff)
        return page_heading("Staff & Duty Roster", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;"><ul>{lis}</ul></div>')
    
    if page_id == "audit_logs":
        query = """
            SELECT al.*, ua.Username 
            FROM AuditLog al 
            LEFT JOIN UserAccount ua ON al.UserID = ua.UserID 
            ORDER BY al.AuditID DESC LIMIT 50
        """
        logs = execute_query(query) or []
        
        body = "".join(f'<tr><td>{esc(str(row["ActionDate"]) if row["ActionDate"] else "N/A")}</td><td>{esc(row["Username"] or "System")}</td><td>{esc(row["Action"])}</td><td>Resource</td></tr>' for row in logs)
        return page_heading("System Audit Logs", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Timestamp</th><th>User</th><th>Action</th><th>Resource</th></tr>{body}</table>')
    
    raise HTTPException(404, "Page not found")

# ==========================================
# Serving Main Frontend
# ==========================================

@app.get("/")
def frontend() -> FileResponse:
    """Serve the main frontend page"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Forensa - Forensic Medical System</h1><p>Frontend not found.</p>")

# Mount static files
app.mount("/pages", StaticFiles(directory=FRONTEND_DIR / "pages"), name="pages")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ==========================================
# Main Entry Point
# ==========================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting server at http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)