from __future__ import annotations

import html
import base64
import hashlib
import hmac
import secrets
from io import BytesIO
from datetime import date, datetime
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager
import mysql.connector
from mysql.connector import Error


import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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
    


PASSWORD_ITERATIONS = 210_000

def hash_password(password: str) -> str:
    """Return a salted PBKDF2-SHA256 password hash."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )

def verify_password(password: str, stored_password: str) -> bool:
    """Verify a PBKDF2 password hash; also accepts legacy plaintext records."""
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored_password)
    try:
        _, iterations_text, salt_text, digest_text = stored_password.split("$", 3)
        expected = base64.b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.b64decode(salt_text),
            int(iterations_text),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def require_permission(user: dict[str, Any], permission_name: str) -> None:
    if not check_permission(user["username"], permission_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission_name} is required.",
        )

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

        # Ensure Doctor users can open and view the Court Reports page.
        doctor_court_permission = """
            SELECT rp.RolePermissionID
            FROM RolePermission rp
            JOIN Role r ON rp.RoleID = r.RoleID
            JOIN Permission p ON rp.PermissionID = p.PermissionID
            WHERE r.RoleName = %s AND p.PermissionName = %s
        """
        if not execute_query(doctor_court_permission, ("Doctor", "Generate Court Reports")):
            add_doctor_court_permission = """
                INSERT INTO RolePermission (RoleID, PermissionID)
                SELECT r.RoleID, p.PermissionID
                FROM Role r CROSS JOIN Permission p
                WHERE r.RoleName = %s AND p.PermissionName = %s
            """
            execute_query(
                add_doctor_court_permission,
                ("Doctor", "Generate Court Reports"),
                fetch=False,
            )

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

class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    nic: str | None = Field(default=None, max_length=20)
    date_of_birth: str | None = None
    gender: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=255)
    contact_no: str | None = Field(default=None, max_length=15)

class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    nic: str | None = Field(default=None, max_length=20)
    date_of_birth: str | None = None
    gender: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=255)
    contact_no: str | None = Field(default=None, max_length=15)

class CourtReportCreate(BaseModel):
    case_id: int
    submission_date: str
    status: str = Field(min_length=2, max_length=50)
    report_content: str = Field(min_length=10, max_length=10000)

class CourtReportUpdate(BaseModel):
    case_id: int | None = None
    submission_date: str | None = None
    status: str | None = Field(default=None, min_length=2, max_length=50)
    report_content: str | None = Field(default=None, min_length=10, max_length=10000)

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
    execute_query(insert_user, (username_lower, hash_password(payload.password), db_role, staff_id), fetch=False)
    
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
    if not result or not verify_password(payload.password, result[0]["Password"]):
        raise HTTPException(401, "Invalid username or password")

    # Transparently upgrade old plaintext passwords after a successful login.
    if not result[0]["Password"].startswith("pbkdf2_sha256$"):
        execute_query(
            "UPDATE UserAccount SET Password = %s WHERE Username = %s",
            (hash_password(payload.password), username_lower),
            fetch=False,
        )

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
# Patient Management API Endpoints
# ==========================================

def _patient_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("PatientID"),
        "full_name": row.get("FullName"),
        "nic": row.get("NIC"),
        "date_of_birth": str(row.get("DateOfBirth")) if row.get("DateOfBirth") else None,
        "gender": row.get("Gender"),
        "address": row.get("Address"),
        "contact_no": row.get("ContactNo"),
        "registration_date": str(row.get("RegistrationDate")) if row.get("RegistrationDate") else None,
    }

@app.get("/api/patients")
def list_patients(search: str | None = None, authorization: str | None = Header(None)) -> list[dict[str, Any]]:
    get_current_user(authorization)
    if search and search.strip():
        term = f"%{search.strip()}%"
        rows = execute_query(
            """
            SELECT * FROM Patient
            WHERE FullName LIKE %s OR NIC LIKE %s OR ContactNo LIKE %s
            ORDER BY PatientID DESC
            """,
            (term, term, term),
        )
    else:
        rows = execute_query("SELECT * FROM Patient ORDER BY PatientID DESC")
    if rows is None:
        raise HTTPException(500, "Unable to load patients")
    return [_patient_to_dict(row) for row in rows]

@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: int, authorization: str | None = Header(None)) -> dict[str, Any]:
    get_current_user(authorization)
    rows = execute_query("SELECT * FROM Patient WHERE PatientID = %s", (patient_id,))
    if not rows:
        raise HTTPException(404, "Patient not found")
    patient = _patient_to_dict(rows[0])
    cases = execute_query(
        """
        SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status
        FROM ForensicCase WHERE PatientID = %s ORDER BY CaseID DESC
        """,
        (patient_id,),
    ) or []
    patient["cases"] = cases
    return patient

@app.post("/api/patients", status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "Manage Cases")
    nic = payload.nic.strip() if payload.nic else None
    if nic and execute_query("SELECT PatientID FROM Patient WHERE NIC = %s", (nic,)):
        raise HTTPException(409, "A patient with this NIC already exists")
    patient_id = execute_query(
        """
        INSERT INTO Patient
            (FullName, NIC, DateOfBirth, Gender, Address, ContactNo, RegistrationDate)
        VALUES (%s, %s, %s, %s, %s, %s, CURDATE())
        """,
        (
            payload.full_name.strip(), nic, payload.date_of_birth or None,
            payload.gender or None, payload.address or None, payload.contact_no or None,
        ),
        fetch=False,
    )
    if not patient_id:
        raise HTTPException(500, "Patient could not be created")
    add_audit("Created Patient", f"Patient ID {patient_id}", user["username"])
    return get_patient(patient_id, authorization)

@app.patch("/api/patients/{patient_id}")
def update_patient(patient_id: int, payload: PatientUpdate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "Manage Cases")
    current_rows = execute_query("SELECT * FROM Patient WHERE PatientID = %s", (patient_id,))
    if not current_rows:
        raise HTTPException(404, "Patient not found")
    current = current_rows[0]
    nic = payload.nic.strip() if payload.nic is not None and payload.nic.strip() else (current.get("NIC") if payload.nic is None else None)
    if nic:
        duplicate = execute_query("SELECT PatientID FROM Patient WHERE NIC = %s AND PatientID <> %s", (nic, patient_id))
        if duplicate:
            raise HTTPException(409, "A patient with this NIC already exists")
    values = (
        payload.full_name.strip() if payload.full_name is not None else current.get("FullName"),
        nic,
        payload.date_of_birth if payload.date_of_birth is not None else current.get("DateOfBirth"),
        payload.gender if payload.gender is not None else current.get("Gender"),
        payload.address if payload.address is not None else current.get("Address"),
        payload.contact_no if payload.contact_no is not None else current.get("ContactNo"),
        patient_id,
    )
    execute_query(
        """
        UPDATE Patient SET FullName=%s, NIC=%s, DateOfBirth=%s, Gender=%s,
                           Address=%s, ContactNo=%s WHERE PatientID=%s
        """,
        values,
        fetch=False,
    )
    add_audit("Updated Patient", f"Patient ID {patient_id}", user["username"])
    return get_patient(patient_id, authorization)

@app.delete("/api/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, authorization: str | None = Header(None)) -> Response:
    user = get_current_user(authorization)
    require_permission(user, "Manage Cases")
    existing = execute_query("SELECT FullName FROM Patient WHERE PatientID = %s", (patient_id,))
    if not existing:
        raise HTTPException(404, "Patient not found")
    linked = execute_query("SELECT COUNT(*) AS total FROM ForensicCase WHERE PatientID = %s", (patient_id,))
    if linked and linked[0]["total"] > 0:
        raise HTTPException(409, "Patient cannot be deleted because forensic cases are linked to this record")
    execute_query("DELETE FROM PatientHistory WHERE PatientID = %s", (patient_id,), fetch=False)
    execute_query("DELETE FROM Patient WHERE PatientID = %s", (patient_id,), fetch=False)
    add_audit("Deleted Patient", existing[0]["FullName"], user["username"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ==========================================
# Reports and Database Backup Endpoints
# ==========================================

def _report_user(authorization: str | None) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "View Reports")
    return user

@app.get("/api/reports/daily")
def daily_case_report(
    report_date: date | None = None,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    user = _report_user(authorization)
    selected_date = report_date or date.today()
    rows = execute_query(
        """
        SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription
        FROM ForensicCase
        WHERE DATE(IncidentDate) = %s
        ORDER BY CaseID DESC
        """,
        (selected_date,),
    )
    if rows is None:
        raise HTTPException(500, "Unable to generate daily report")
    add_audit("Viewed Daily Case Report", str(selected_date), user["username"])
    return {"report_type": "daily", "date": str(selected_date), "total_cases": len(rows), "cases": rows}

@app.get("/api/reports/monthly")
def monthly_case_report(
    year: int | None = None,
    month: int | None = None,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    user = _report_user(authorization)
    today = date.today()
    selected_year = year or today.year
    selected_month = month or today.month
    if selected_month < 1 or selected_month > 12:
        raise HTTPException(400, "Month must be between 1 and 12")
    rows = execute_query(
        """
        SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription
        FROM ForensicCase
        WHERE YEAR(IncidentDate) = %s AND MONTH(IncidentDate) = %s
        ORDER BY IncidentDate DESC, CaseID DESC
        """,
        (selected_year, selected_month),
    )
    if rows is None:
        raise HTTPException(500, "Unable to generate monthly report")
    status_summary: dict[str, int] = {}
    for row in rows:
        key = row.get("Status") or "Unknown"
        status_summary[key] = status_summary.get(key, 0) + 1
    add_audit("Viewed Monthly Report", f"{selected_year}-{selected_month:02d}", user["username"])
    return {
        "report_type": "monthly",
        "year": selected_year,
        "month": selected_month,
        "total_cases": len(rows),
        "status_summary": status_summary,
        "cases": rows,
    }

@app.get("/api/reports/pending")
def pending_cases_report(authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _report_user(authorization)
    rows = execute_query(
        """
        SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription
        FROM ForensicCase
        WHERE LOWER(Status) IN ('pending', 'open', 'active', 'in progress', 'under investigation')
        ORDER BY IncidentDate ASC, CaseID ASC
        """
    )
    if rows is None:
        raise HTTPException(500, "Unable to generate pending cases report")
    add_audit("Viewed Pending Cases Report", f"{len(rows)} cases", user["username"])
    return {"report_type": "pending_cases", "total_cases": len(rows), "cases": rows}

@app.get("/api/reports/court")
def court_report(authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "Generate Court Reports")
    rows = execute_query(
        """
        SELECT cr.CourtReportID, fc.CaseNumber, fc.CaseType,
               cr.SubmissionDate, cr.Status, cr.ReportContent,
               c.CourtName, c.Location AS CourtLocation, cc.HearingDate
        FROM CourtReport cr
        JOIN ForensicCase fc ON cr.CaseID = fc.CaseID
        LEFT JOIN CaseCourt cc ON fc.CaseID = cc.CaseID
        LEFT JOIN Court c ON cc.CourtID = c.CourtID
        ORDER BY COALESCE(cc.HearingDate, cr.SubmissionDate) DESC
        """
    )
    if rows is None:
        raise HTTPException(500, "Unable to generate court report")
    add_audit("Viewed Court Report", f"{len(rows)} records", user["username"])
    return {"report_type": "court", "total_reports": len(rows), "reports": rows}

@app.get("/api/reports/statistical")
def statistical_report(authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _report_user(authorization)
    totals = execute_query("SELECT COUNT(*) AS total_cases FROM ForensicCase") or [{"total_cases": 0}]
    by_status = execute_query(
        "SELECT COALESCE(Status, 'Unknown') AS label, COUNT(*) AS total FROM ForensicCase GROUP BY Status ORDER BY total DESC"
    ) or []
    by_type = execute_query(
        "SELECT COALESCE(CaseType, 'Unknown') AS label, COUNT(*) AS total FROM ForensicCase GROUP BY CaseType ORDER BY total DESC"
    ) or []
    monthly_trend = execute_query(
        """
        SELECT DATE_FORMAT(IncidentDate, '%Y-%m') AS month, COUNT(*) AS total
        FROM ForensicCase
        WHERE IncidentDate >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH)
        GROUP BY DATE_FORMAT(IncidentDate, '%Y-%m')
        ORDER BY month
        """
    ) or []
    add_audit("Viewed Statistical Report", "Case statistics", user["username"])
    return {
        "report_type": "statistical",
        "total_cases": totals[0]["total_cases"],
        "cases_by_status": by_status,
        "cases_by_type": by_type,
        "monthly_trend": monthly_trend,
    }


def _pdf_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _build_report_pdf(title: str, subtitle: str, columns: list[str], rows: list[list[Any]], generated_by: str, summary_lines: list[str] | None = None, landscape_mode: bool = True) -> BytesIO:
    buffer = BytesIO()
    pagesize = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm, title=title, author="Forensa")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ForensaTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=4)
    subtitle_style = ParagraphStyle("ForensaSubtitle", parent=styles["Heading2"], alignment=TA_CENTER, fontSize=11, leading=14, textColor=colors.HexColor("#333333"), spaceAfter=10)
    small = ParagraphStyle("ForensaSmall", parent=styles["BodyText"], fontSize=8, leading=10)
    story = [Paragraph("FORENSA", title_style), Paragraph("Forensic Medicine Management System", subtitle_style), Paragraph(title, styles["Heading1"]), Paragraph(subtitle, styles["BodyText"]), Spacer(1,6), Paragraph(f"Generated by: {_pdf_text(generated_by)}", small), Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", small), Spacer(1,10)]
    if summary_lines:
        for line in summary_lines:
            story.append(Paragraph(html.escape(_pdf_text(line)), styles["BodyText"]))
        story.append(Spacer(1,8))
    table_data = [[Paragraph(html.escape(str(c)), small) for c in columns]]
    for row in rows:
        table_data.append([Paragraph(html.escape(_pdf_text(v)), small) for v in row])
    if len(table_data) == 1:
        table_data.append([Paragraph("No records found", small)] + ["" for _ in columns[1:]])
    available_width = pagesize[0] - 28*mm
    table = Table(table_data, repeatRows=1, colWidths=[available_width/max(len(columns),1)]*len(columns))
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#260099")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#999999")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f3fb")]),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(table)
    def footer(canvas, doc_obj):
        canvas.saveState(); canvas.setFont("Helvetica",8); canvas.drawString(14*mm,8*mm,"Confidential – Authorized Forensa users only"); canvas.drawRightString(pagesize[0]-14*mm,8*mm,f"Page {doc_obj.page}"); canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer


def _pdf_response(buffer: BytesIO, filename: str) -> StreamingResponse:
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/reports/daily/pdf")
def download_daily_case_report_pdf(report_date: date | None = None, authorization: str | None = Header(None)):
    user = _report_user(authorization); selected_date = report_date or date.today()
    rows = execute_query("""SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription FROM ForensicCase WHERE DATE(IncidentDate) = %s ORDER BY CaseID DESC""", (selected_date,))
    if rows is None: raise HTTPException(500, "Unable to generate daily report PDF")
    data = [[r.get("CaseID"),r.get("CaseNumber"),r.get("CaseType"),r.get("IncidentDate"),r.get("Status"),r.get("CaseDescription")] for r in rows]
    pdf = _build_report_pdf("Daily Case Report", f"Report date: {selected_date}", ["Case ID","Case Number","Case Type","Incident Date","Status","Description"], data, user["username"], [f"Total cases: {len(rows)}"])
    add_audit("Downloaded Daily Case Report PDF", str(selected_date), user["username"])
    return _pdf_response(pdf, f"Daily_Case_Report_{selected_date}.pdf")


@app.get("/api/reports/monthly/pdf")
def download_monthly_report_pdf(year: int | None = None, month: int | None = None, authorization: str | None = Header(None)):
    user = _report_user(authorization); today = date.today(); selected_year = year or today.year; selected_month = month or today.month
    if selected_month < 1 or selected_month > 12: raise HTTPException(400, "Month must be between 1 and 12")
    rows = execute_query("""SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription FROM ForensicCase WHERE YEAR(IncidentDate) = %s AND MONTH(IncidentDate) = %s ORDER BY IncidentDate DESC, CaseID DESC""", (selected_year, selected_month))
    if rows is None: raise HTTPException(500, "Unable to generate monthly report PDF")
    status_summary = {}
    for row in rows:
        key = row.get("Status") or "Unknown"; status_summary[key] = status_summary.get(key,0)+1
    data = [[r.get("CaseID"),r.get("CaseNumber"),r.get("CaseType"),r.get("IncidentDate"),r.get("Status"),r.get("CaseDescription")] for r in rows]
    summary = [f"Total cases: {len(rows)}", "Status summary: " + ", ".join(f"{k}: {v}" for k,v in status_summary.items())]
    pdf = _build_report_pdf("Monthly Case Report", f"Period: {selected_year}-{selected_month:02d}", ["Case ID","Case Number","Case Type","Incident Date","Status","Description"], data, user["username"], summary)
    add_audit("Downloaded Monthly Report PDF", f"{selected_year}-{selected_month:02d}", user["username"])
    return _pdf_response(pdf, f"Monthly_Report_{selected_year}_{selected_month:02d}.pdf")


@app.get("/api/reports/pending/pdf")
def download_pending_cases_report_pdf(authorization: str | None = Header(None)):
    user = _report_user(authorization)
    rows = execute_query("""SELECT CaseID, CaseNumber, CaseType, IncidentDate, Status, CaseDescription FROM ForensicCase WHERE LOWER(Status) IN ('pending','open','active','in progress','under investigation') ORDER BY IncidentDate ASC, CaseID ASC""")
    if rows is None: raise HTTPException(500, "Unable to generate pending cases report PDF")
    data = [[r.get("CaseID"),r.get("CaseNumber"),r.get("CaseType"),r.get("IncidentDate"),r.get("Status"),r.get("CaseDescription")] for r in rows]
    pdf = _build_report_pdf("Pending Cases Report", "Cases awaiting completion or further action", ["Case ID","Case Number","Case Type","Incident Date","Status","Description"], data, user["username"], [f"Total pending cases: {len(rows)}"])
    add_audit("Downloaded Pending Cases Report PDF", f"{len(rows)} cases", user["username"])
    return _pdf_response(pdf, f"Pending_Cases_Report_{date.today()}.pdf")


@app.get("/api/reports/court/pdf")
def download_court_report_pdf(authorization: str | None = Header(None)):
    user = get_current_user(authorization); require_permission(user, "Generate Court Reports")
    rows = execute_query("""SELECT cr.CourtReportID, fc.CaseNumber, fc.CaseType, cr.SubmissionDate, cr.Status, cr.ReportContent, c.CourtName, c.Location AS CourtLocation, cc.HearingDate FROM CourtReport cr JOIN ForensicCase fc ON cr.CaseID = fc.CaseID LEFT JOIN CaseCourt cc ON fc.CaseID = cc.CaseID LEFT JOIN Court c ON cc.CourtID = c.CourtID ORDER BY COALESCE(cc.HearingDate, cr.SubmissionDate) DESC""")
    if rows is None: raise HTTPException(500, "Unable to generate court report PDF")
    data = [[r.get("CourtReportID"),r.get("CaseNumber"),r.get("CaseType"),r.get("CourtName"),r.get("HearingDate"),r.get("SubmissionDate"),r.get("Status"),r.get("ReportContent")] for r in rows]
    pdf = _build_report_pdf("Court Report", "Court submissions, hearing details and report status", ["Report ID","Case Number","Case Type","Court","Hearing Date","Submitted","Status","Report Content"], data, user["username"], [f"Total court reports: {len(rows)}"])
    add_audit("Downloaded Court Report PDF", f"{len(rows)} records", user["username"])
    return _pdf_response(pdf, f"Court_Report_{date.today()}.pdf")


@app.get("/api/reports/statistical/pdf")
def download_statistical_report_pdf(authorization: str | None = Header(None)):
    user = _report_user(authorization)
    totals = execute_query("SELECT COUNT(*) AS total_cases FROM ForensicCase") or [{"total_cases":0}]
    by_status = execute_query("SELECT COALESCE(Status,'Unknown') AS label, COUNT(*) AS total FROM ForensicCase GROUP BY Status ORDER BY total DESC") or []
    by_type = execute_query("SELECT COALESCE(CaseType,'Unknown') AS label, COUNT(*) AS total FROM ForensicCase GROUP BY CaseType ORDER BY total DESC") or []
    trend = execute_query("""SELECT DATE_FORMAT(IncidentDate,'%Y-%m') AS month, COUNT(*) AS total FROM ForensicCase WHERE IncidentDate >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH) GROUP BY DATE_FORMAT(IncidentDate,'%Y-%m') ORDER BY month""") or []
    data = [["Cases by Status",r.get("label"),r.get("total")] for r in by_status] + [["Cases by Type",r.get("label"),r.get("total")] for r in by_type] + [["Monthly Trend",r.get("month"),r.get("total")] for r in trend]
    pdf = _build_report_pdf("Statistical Report", "Summary of forensic case activity", ["Category","Label / Period","Total"], data, user["username"], [f"Total cases in database: {totals[0].get('total_cases',0)}"], landscape_mode=False)
    add_audit("Downloaded Statistical Report PDF", "Case statistics", user["username"])
    return _pdf_response(pdf, f"Statistical_Report_{date.today()}.pdf")


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (datetime, date)):
        value = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"

@app.post("/api/admin/database-backup")
def create_database_backup(authorization: str | None = Header(None)) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "Manage Users")

    connection = get_db_connection()
    if not connection:
        raise HTTPException(500, "Database connection failed")

    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{DB_CONFIG['database']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    backup_path = backup_dir / filename

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        table_rows = cursor.fetchall()
        table_key = next(iter(table_rows[0])) if table_rows else None
        tables = [row[table_key] for row in table_rows] if table_key else []

        with backup_path.open("w", encoding="utf-8") as output:
            output.write(f"-- Backup of {DB_CONFIG['database']} generated {datetime.now().isoformat()}\n")
            output.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_row = cursor.fetchone()
                create_sql = create_row.get("Create Table")
                output.write(f"DROP TABLE IF EXISTS `{table}`;\n{create_sql};\n\n")

                cursor.execute(f"SELECT * FROM `{table}`")
                records = cursor.fetchall()
                for record in records:
                    columns = ", ".join(f"`{name}`" for name in record.keys())
                    values = ", ".join(_sql_literal(value) for value in record.values())
                    output.write(f"INSERT INTO `{table}` ({columns}) VALUES ({values});\n")
                output.write("\n")
            output.write("SET FOREIGN_KEY_CHECKS=1;\n")
        cursor.close()
        connection.close()
    except Exception as exc:
        connection.close()
        if backup_path.exists():
            backup_path.unlink()
        raise HTTPException(500, f"Backup failed: {exc}") from exc

    add_audit("Created Database Backup", filename, user["username"])
    return {"message": "Database backup created", "filename": filename, "location": str(backup_path)}

# ==========================================
# Court Report Management API
# ==========================================

def _court_report_user(authorization: str | None) -> dict[str, Any]:
    user = get_current_user(authorization)
    require_permission(user, "Generate Court Reports")
    return user

@app.get("/api/court-reports/{report_id}")
def get_court_report(report_id: int, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _court_report_user(authorization)
    rows = execute_query("""
        SELECT cr.CourtReportID, cr.CaseID, fc.CaseNumber, fc.CaseType,
               cr.SubmissionDate, cr.Status, cr.ReportContent
        FROM CourtReport cr
        LEFT JOIN ForensicCase fc ON cr.CaseID = fc.CaseID
        WHERE cr.CourtReportID = %s
    """, (report_id,))
    if not rows:
        raise HTTPException(404, "Court report not found")
    add_audit("Viewed Court Report", f"CR-{report_id}", user["username"])
    return rows[0]

@app.post("/api/court-reports", status_code=status.HTTP_201_CREATED)
def create_court_report(payload: CourtReportCreate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _court_report_user(authorization)
    case_rows = execute_query("SELECT CaseID, CaseNumber FROM ForensicCase WHERE CaseID = %s", (payload.case_id,))
    if not case_rows:
        raise HTTPException(400, "Selected forensic case does not exist")
    allowed = {"Draft", "Pending Review", "Approved", "Submitted", "Returned"}
    if payload.status not in allowed:
        raise HTTPException(400, "Invalid court report status")
    report_id = execute_query("""
        INSERT INTO CourtReport (CaseID, SubmissionDate, Status, ReportContent)
        VALUES (%s, %s, %s, %s)
    """, (payload.case_id, payload.submission_date, payload.status, payload.report_content.strip()), fetch=False)
    if not report_id:
        raise HTTPException(500, "Unable to save court report")
    add_audit("Created Court Report", f"CR-{report_id} for {case_rows[0]['CaseNumber']}", user["username"])
    return {"message": "Court report created successfully", "id": report_id}

@app.patch("/api/court-reports/{report_id}")
def update_court_report(report_id: int, payload: CourtReportUpdate, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _court_report_user(authorization)
    rows = execute_query("SELECT * FROM CourtReport WHERE CourtReportID = %s", (report_id,))
    if not rows:
        raise HTTPException(404, "Court report not found")
    old = rows[0]
    case_id = payload.case_id if payload.case_id is not None else old["CaseID"]
    submitted = payload.submission_date if payload.submission_date is not None else old["SubmissionDate"]
    report_status = payload.status if payload.status is not None else old["Status"]
    content = payload.report_content.strip() if payload.report_content is not None else old["ReportContent"]
    if not execute_query("SELECT CaseID FROM ForensicCase WHERE CaseID = %s", (case_id,)):
        raise HTTPException(400, "Selected forensic case does not exist")
    if report_status not in {"Draft", "Pending Review", "Approved", "Submitted", "Returned"}:
        raise HTTPException(400, "Invalid court report status")
    execute_query("""UPDATE CourtReport SET CaseID=%s, SubmissionDate=%s, Status=%s, ReportContent=%s WHERE CourtReportID=%s""",
                  (case_id, submitted, report_status, content, report_id), fetch=False)
    add_audit("Updated Court Report", f"CR-{report_id}", user["username"])
    return {"message": "Court report updated successfully"}

@app.delete("/api/court-reports/{report_id}")
def delete_court_report(report_id: int, authorization: str | None = Header(None)) -> dict[str, Any]:
    user = _court_report_user(authorization)
    if not execute_query("SELECT CourtReportID FROM CourtReport WHERE CourtReportID = %s", (report_id,)):
        raise HTTPException(404, "Court report not found")
    execute_query("DELETE FROM CourtReport WHERE CourtReportID = %s", (report_id,), fetch=False)
    add_audit("Deleted Court Report", f"CR-{report_id}", user["username"])
    return {"message": "Court report deleted successfully"}

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
        "laboratory": "Perform Laboratory Tests",
        "court_reports": "Generate Court Reports",
        "reports": "View Reports",
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

    # Evidence Officers may view case records, but cannot create, edit, or delete them.
    if page_id == "cases" and not (
        check_permission(user["username"], "Manage Cases")
        or user.get("role") == "Evidence Officer"
    ):
        raise HTTPException(403, "Permission denied to view cases")

    # Patient management is available to clinical/case-management roles.
    if page_id == "patients" and not (
        check_permission(user["username"], "Manage Cases")
        or user.get("role") in {"JMO", "Doctor", "Administrator"}
    ):
        raise HTTPException(403, "Permission denied to view patients")
    
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
    
    if page_id == "patients":
        can_manage = check_permission(user["username"], "Manage Cases")
        patients = execute_query("SELECT * FROM Patient ORDER BY PatientID DESC LIMIT 100") or []
        add_button = ""
        form_html = ""
        if can_manage:
            add_button = '<button onclick="togglePatientForm()" style="background:#260099;color:white;border:0;padding:8px 20px;font-weight:bold;cursor:pointer;margin-bottom:15px;">+ Add New Patient</button>'
            form_html = """
            <div id="patient-form-container" style="display:none;background:#f9f9fb;border:1px solid #c9c1b0;padding:20px;margin-bottom:15px;">
              <h3 id="patient-form-title" style="margin-top:0;color:#260099;">Add New Patient</h3>
              <form onsubmit="handleSavePatient(event)">
                <input type="hidden" id="patient-id">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                  <div><label><strong>Full Name</strong></label><input id="patient-full-name" required style="width:100%;padding:7px;box-sizing:border-box;"></div>
                  <div><label><strong>NIC</strong></label><input id="patient-nic" maxlength="20" style="width:100%;padding:7px;box-sizing:border-box;"></div>
                  <div><label><strong>Date of Birth</strong></label><input id="patient-dob" type="date" style="width:100%;padding:7px;box-sizing:border-box;"></div>
                  <div><label><strong>Gender</strong></label><select id="patient-gender" style="width:100%;padding:7px;box-sizing:border-box;"><option value="">Select</option><option>Male</option><option>Female</option><option>Other</option></select></div>
                  <div><label><strong>Contact Number</strong></label><input id="patient-contact" maxlength="15" style="width:100%;padding:7px;box-sizing:border-box;"></div>
                  <div><label><strong>Address</strong></label><input id="patient-address" maxlength="255" style="width:100%;padding:7px;box-sizing:border-box;"></div>
                </div>
                <div style="margin-top:15px;"><button type="submit" style="background:#260099;color:white;border:0;padding:8px 20px;cursor:pointer;">Save Patient</button><button type="button" onclick="resetPatientForm()" style="margin-left:8px;padding:8px 20px;border:0;cursor:pointer;">Cancel</button></div>
              </form>
            </div>
            """
        rows = ""
        for row in patients:
            actions = f'<button onclick="viewPatient({row["PatientID"]})" style="background:#004488;color:white;border:0;padding:5px 10px;cursor:pointer;">View</button>'
            if can_manage:
                actions += f' <button onclick="editPatient({row["PatientID"]})" style="background:#8a5a00;color:white;border:0;padding:5px 10px;cursor:pointer;">Edit</button> <button onclick="deletePatient({row["PatientID"]})" style="background:#a00020;color:white;border:0;padding:5px 10px;cursor:pointer;">Delete</button>'
            rows += f'<tr><td>{row["PatientID"]}</td><td>{esc(row["FullName"])}</td><td>{esc(row["NIC"] or "-")}</td><td>{esc(row["DateOfBirth"] or "-")}</td><td>{esc(row["Gender"] or "-")}</td><td>{esc(row["ContactNo"] or "-")}</td><td>{actions}</td></tr>'
        search = '<input id="patient-search" oninput="filterPatientTable()" placeholder="Search by name, NIC or contact number" style="width:100%;padding:8px;margin-bottom:12px;box-sizing:border-box;">'
        table = f'<div style="overflow-x:auto;"><table id="patient-table" border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><thead><tr style="background:#260099;color:white;"><th>ID</th><th>Full Name</th><th>NIC</th><th>Date of Birth</th><th>Gender</th><th>Contact</th><th>Actions</th></tr></thead><tbody>{rows or "<tr><td colspan=\"7\">No patient records found.</td></tr>"}</tbody></table></div>'
        return page_heading("Patient Management", add_button + form_html + search + table)

    if page_id == "laboratory":
        query = "SELECT * FROM LaboratoryTest ORDER BY TestID DESC"
        tests = execute_query(query) or []
        
        body = "".join(f'<tr><td>LAB-{esc(str(row["TestID"]))}</td><td>{esc(row["TestType"])}</td><td>Analyst</td><td><strong>{esc("Completed" if row["Result"] else "In Progress")}</strong></td></tr>' for row in tests)
        return page_heading("Laboratory Services", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Request ID</th><th>Sample Type</th><th>Assigned Analyst</th><th>Status</th></tr>{body}</table>')
    
    if page_id == "reports":
        today = date.today()
        report_html = f"""
        <div style="background:white;border:1px solid #e0dacb;padding:20px;">
            <p style="font-size:13px;margin-top:0;">Generate and download official PDF reports. All downloads are recorded in the audit log.</p>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px;">
                <div style="border:1px solid #ddd;padding:15px;border-radius:4px;"><h3 style="margin-top:0;color:#260099;">Daily Case Report</h3><input id="daily-report-date" type="date" value="{today.isoformat()}" style="width:100%;padding:7px;margin-bottom:10px;box-sizing:border-box;"><button onclick="downloadReportPdf('daily')" style="background:#260099;color:white;border:0;padding:8px 14px;cursor:pointer;">Download PDF</button></div>
                <div style="border:1px solid #ddd;padding:15px;border-radius:4px;"><h3 style="margin-top:0;color:#260099;">Monthly Report</h3><div style="display:flex;gap:8px;margin-bottom:10px;"><input id="monthly-report-year" type="number" value="{today.year}" min="2000" max="2100" style="width:55%;padding:7px;box-sizing:border-box;"><input id="monthly-report-month" type="number" value="{today.month}" min="1" max="12" style="width:45%;padding:7px;box-sizing:border-box;"></div><button onclick="downloadReportPdf('monthly')" style="background:#260099;color:white;border:0;padding:8px 14px;cursor:pointer;">Download PDF</button></div>
                <div style="border:1px solid #ddd;padding:15px;border-radius:4px;"><h3 style="margin-top:0;color:#260099;">Pending Cases</h3><p style="font-size:12px;">Pending, active, open and under-investigation cases.</p><button onclick="downloadReportPdf('pending')" style="background:#260099;color:white;border:0;padding:8px 14px;cursor:pointer;">Download PDF</button></div>
                <div style="border:1px solid #ddd;padding:15px;border-radius:4px;"><h3 style="margin-top:0;color:#260099;">Court Report</h3><p style="font-size:12px;">Court submissions, hearings and report status.</p><button onclick="downloadReportPdf('court')" style="background:#260099;color:white;border:0;padding:8px 14px;cursor:pointer;">Download PDF</button></div>
                <div style="border:1px solid #ddd;padding:15px;border-radius:4px;"><h3 style="margin-top:0;color:#260099;">Statistical Report</h3><p style="font-size:12px;">Cases by status, type and monthly trend.</p><button onclick="downloadReportPdf('statistical')" style="background:#260099;color:white;border:0;padding:8px 14px;cursor:pointer;">Download PDF</button></div>
            </div><div id="report-download-status" style="margin-top:15px;font-size:13px;"></div>
        </div>
        """
        return page_heading("Reports Centre", report_html)

    if page_id == "court_reports":
        reports = execute_query("""
            SELECT cr.CourtReportID, cr.CaseID, fc.CaseNumber, fc.CaseType,
                   cr.SubmissionDate, cr.Status, cr.ReportContent
            FROM CourtReport cr
            LEFT JOIN ForensicCase fc ON cr.CaseID = fc.CaseID
            ORDER BY cr.CourtReportID DESC
        """) or []
        cases_list = execute_query("SELECT CaseID, CaseNumber, CaseType FROM ForensicCase ORDER BY CaseID DESC") or []
        options = "".join(f'<option value="{r["CaseID"]}">{esc(r["CaseNumber"])} — {esc(r["CaseType"] or "Unknown")}</option>' for r in cases_list)
        total = len(reports)
        drafts = sum(1 for r in reports if (r.get("Status") or "").lower() == "draft")
        submitted = sum(1 for r in reports if (r.get("Status") or "").lower() == "submitted")
        pending = sum(1 for r in reports if (r.get("Status") or "").lower() in {"pending", "pending review"})
        rows_html = "".join(
            f'''<tr data-report-row>
            <td style="padding:9px;font-weight:bold;color:#260099;">CR-{esc(str(r["CourtReportID"]))}</td>
            <td style="padding:9px;"><strong>{esc(r["CaseNumber"] or "Unlinked")}</strong><br><small>{esc(r["CaseType"] or "Unknown")}</small></td>
            <td style="padding:9px;">{esc(str(r["SubmissionDate"]) if r["SubmissionDate"] else "Not set")}</td>
            <td style="padding:9px;"><span style="background:#eee;padding:4px 8px;border-radius:12px;font-weight:bold;font-size:11px;">{esc(r["Status"] or "Draft")}</span></td>
            <td style="padding:9px;max-width:360px;white-space:normal;">{esc(r["ReportContent"] or "No content")}</td>
            <td style="padding:9px;white-space:nowrap;"><button onclick="viewCourtReport({r["CourtReportID"]})">View</button> <button onclick="editCourtReport({r["CourtReportID"]})">Edit</button> <button onclick="deleteCourtReport({r["CourtReportID"]})" style="background:#b00020;color:white;border:0;padding:5px 8px;">Delete</button></td>
            </tr>''' for r in reports
        ) or '<tr><td colspan="6" style="padding:35px;text-align:center;color:#666;">No court reports yet. Click <strong>+ Add Court Report</strong>.</td></tr>'
        body = f'''
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:15px;">
          <p style="margin:0;color:#555;">Create, review and submit official forensic court reports.</p>
          <div><button type="button" onclick="downloadReportPdf('court')" style="padding:9px 12px;background:white;color:#260099;border:1px solid #260099;">Download PDF</button> <a href="#court-report-create" style="display:inline-block;padding:10px 15px;background:#260099;color:white;text-decoration:none;font-weight:bold;">+ Add Court Report</a></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:15px;">
          <div style="background:white;border-left:4px solid #260099;padding:13px;"><small>Total Reports</small><div style="font-size:25px;font-weight:bold;">{total}</div></div>
          <div style="background:white;border-left:4px solid #777;padding:13px;"><small>Drafts</small><div style="font-size:25px;font-weight:bold;">{drafts}</div></div>
          <div style="background:white;border-left:4px solid #cc8800;padding:13px;"><small>Pending Review</small><div style="font-size:25px;font-weight:bold;">{pending}</div></div>
          <div style="background:white;border-left:4px solid #16833b;padding:13px;"><small>Submitted</small><div style="font-size:25px;font-weight:bold;">{submitted}</div></div>
        </div>
        <details id="court-report-create" style="background:#f7f5fc;border:1px solid #cbc3e4;padding:18px;margin-bottom:15px;" open>
          <summary style="cursor:pointer;font-size:18px;font-weight:bold;color:#260099;margin-bottom:14px;">Create New Court Report</summary>
          <form onsubmit="handleCreateCourtReport(event)">
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;">
              <div><label><strong>Forensic Case *</strong></label><select id="court-case-id" required style="width:100%;padding:9px;margin-top:4px;"><option value="">Select case</option>{options}</select></div>
              <div><label><strong>Submission Date *</strong></label><input id="court-submission-date" type="date" value="{date.today().isoformat()}" required style="width:100%;padding:9px;margin-top:4px;box-sizing:border-box;"></div>
              <div><label><strong>Status *</strong></label><select id="court-status" style="width:100%;padding:9px;margin-top:4px;"><option>Draft</option><option>Pending Review</option><option>Approved</option><option>Submitted</option><option>Returned</option></select></div>
            </div>
            <div style="margin-top:11px;"><label><strong>Medical Findings and Court Report Content *</strong></label><textarea id="court-report-content" minlength="10" required rows="8" style="width:100%;padding:9px;margin-top:4px;box-sizing:border-box;" placeholder="Enter examination findings, medical opinion, conclusions and information prepared for court..."></textarea></div>
            <div id="court-form-message" style="margin-top:8px;"></div><div style="margin-top:10px;"><button type="submit" style="background:#260099;color:white;border:0;padding:9px 16px;">Save Court Report</button> <button type="button" onclick="document.getElementById('court-report-create').removeAttribute('open')" style="padding:9px 16px;">Cancel</button></div>
          </form>
        </details>
        <div style="background:white;border:1px solid #ddd;padding:13px;"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:10px;"><h3 style="margin:0;color:#260099;">Court Report Register</h3><input id="court-report-search" oninput="filterCourtReports()" placeholder="Search reports..." style="padding:8px;min-width:260px;"></div><div style="overflow-x:auto;"><table id="court-report-table" style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#260099;color:white;text-align:left;"><th style="padding:9px;">Report No.</th><th style="padding:9px;">Case</th><th style="padding:9px;">Date</th><th style="padding:9px;">Status</th><th style="padding:9px;">Report Content</th><th style="padding:9px;">Actions</th></tr></thead><tbody>{rows_html}</tbody></table></div></div>
        '''
        return page_heading("Court Reports & Testimonies", body)

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