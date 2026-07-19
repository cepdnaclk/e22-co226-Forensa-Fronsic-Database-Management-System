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

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "docs" / "Code" / "frontend"

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ForensicMedicalDB'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306))
}

print("=" * 60)
print("🔬 Starting Forensa Application")
print("=" * 60)
print(f"📊 Database: {DB_CONFIG['database']}")
print(f"👤 User: {DB_CONFIG['user']}")
print(f"🌐 Host: {DB_CONFIG['host']}")
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
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def execute_query(query, params=None, fetch=True):
    """Execute a query and return results with proper error handling"""
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database")
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
        print(f"❌ Error executing query: {e}")
        print(f"Query: {query[:200]}...")
        if params:
            print(f"Params: {params}")
        if connection:
            connection.rollback()
            connection.close()
        return None

def add_audit(action: str, resource: str) -> None:
    """Add an audit log entry to database"""
    try:
        # Get the current user (for now using default)
        username = "system_user"
        
        # Query to get user_id from username
        user_query = "SELECT UserID FROM UserAccount WHERE Username = %s"
        user_result = execute_query(user_query, (username,))
        
        user_id = user_result[0]["UserID"] if user_result else 1
        
        insert_query = """
            INSERT INTO AuditLog (UserID, Action, ActionDate)
            VALUES (%s, %s, %s)
        """
        
        # Format action with resource
        full_action = f"{action}: {resource}"
        current_time = datetime.now()
        
        execute_query(insert_query, (user_id, full_action, current_time), fetch=False)
    except Exception as e:
        print(f"⚠️ Error adding audit log: {e}")

# ==========================================
# Database Initialization
# ==========================================

def init_database():
    """Initialize database and add sample data if needed"""
    try:
        # First check if database exists
        connection = get_db_connection()
        if not connection:
            print("❌ Could not connect to MySQL. Please check your credentials.")
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
            print("⚠️  TABLES NOT FOUND!")
            print("=" * 60)
            print(f"Please create the tables in database: {DB_CONFIG['database']}")
            print("Run your SQL script to create all tables.")
            print("=" * 60)
            return
        
        print("✅ Tables found in database.")
        
        # Check if we need to add sample data
        check_cases = "SELECT COUNT(*) as count FROM ForensicCase"
        count = execute_query(check_cases)
        
        if count and count[0]["count"] == 0:
            print("📝 Adding sample data...")
            
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
            
            print("✅ Sample data added successfully")
        
        print("✅ Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# ==========================================
# Lifespan Event
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Forensa application...")
    init_database()
    yield
    # Shutdown
    print("👋 Shutting down application...")

# ==========================================
# FastAPI App Initialization
# ==========================================

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

# ==========================================
# Helper Functions
# ==========================================

def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))

def page_heading(title: str, body: str) -> str:
    return f'<h2 style="color:#260099;border-bottom:2px solid #260099;margin-top:0;padding-bottom:5px;font-size:18px;">{esc(title)}</h2>{body}'

def find_case(case_id: int) -> dict[str, Any]:
    """Find a case by ID from database"""
    query = "SELECT * FROM ForensicCase WHERE CaseID = %s"
    result = execute_query(query, (case_id,))
    
    if not result:
        raise HTTPException(404, "Case not found")
    
    row = result[0]
    
    return {
        "id": row["CaseID"],
        "case_number": row["CaseNumber"],
        "title": row["CaseDescription"][:50] if row["CaseDescription"] else "Untitled",
        "case_type": row["CaseType"] or "Unknown",
        "status": row["Status"] or "Unknown",
        "assigned_to": "Unassigned",
        "opened_date": str(row["IncidentDate"]) if row["IncidentDate"] else None,
        "description": row["CaseDescription"] or ""
    }

# ==========================================
# API Endpoints
# ==========================================

@app.get("/api/health")
def health() -> dict[str, str]:
    """Health check endpoint"""
    connection = get_db_connection()
    db_status = "connected" if connection else "disconnected"
    if connection:
        connection.close()
    return {"status": "ok", "storage": "mysql", "database": db_status}

@app.get("/api/test-db")
def test_db():
    """Test database connection"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            return {"status": "success", "message": "Database connected successfully"}
        else:
            return {"status": "error", "message": "Database connection failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# Cases Endpoints
# ==========================================

@app.get("/api/cases")
def list_cases(status_filter: str | None = None):
    """Get all cases from database"""
    try:
        query = "SELECT * FROM ForensicCase"
        if status_filter:
            query += f" WHERE Status = '{status_filter}'"
        query += " ORDER BY CaseID DESC"
        
        result = execute_query(query)
        if result is None:
            raise HTTPException(500, "Database query failed")
        
        cases = []
        for row in result:
            cases.append({
                "id": row["CaseID"],
                "case_number": row["CaseNumber"],
                "title": row["CaseDescription"][:50] if row["CaseDescription"] else "Untitled",
                "case_type": row["CaseType"] or "Unknown",
                "status": row["Status"] or "Unknown",
                "assigned_to": "Unassigned",
                "opened_date": str(row["IncidentDate"]) if row["IncidentDate"] else None,
                "description": row["CaseDescription"] or ""
            })
        return cases
    except Exception as e:
        print(f"❌ Error in list_cases: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/cases/{case_id}")
def get_case(case_id: int):
    """Get a specific case from database"""
    try:
        return find_case(case_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_case: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/cases", status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate):
    """Create a new case in database"""
    try:
        # Check if case number exists
        check_query = "SELECT COUNT(*) as count FROM ForensicCase WHERE CaseNumber = %s"
        result = execute_query(check_query, (payload.case_number,))
        
        if result and result[0]["count"] > 0:
            raise HTTPException(409, "Case number already exists")
        
        # Convert date string to date object
        try:
            incident_date = datetime.strptime(payload.opened_date, "%Y-%m-%d").date()
        except:
            incident_date = datetime.now().date()
        
        insert_query = """
            INSERT INTO ForensicCase 
            (CaseNumber, CaseType, IncidentDate, CaseDescription, Status)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        params = (
            payload.case_number,
            payload.case_type,
            incident_date,
            payload.description or payload.title,
            payload.status
        )
        
        case_id = execute_query(insert_query, params, fetch=False)
        
        if not case_id:
            raise HTTPException(500, "Failed to create case")
        
        add_audit("Created Case", payload.case_number)
        
        return get_case(case_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in create_case: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

@app.patch("/api/cases/{case_id}")
def update_case(case_id: int, payload: CaseUpdate):
    """Update an existing case"""
    try:
        # Check if case exists
        check_query = "SELECT * FROM ForensicCase WHERE CaseID = %s"
        result = execute_query(check_query, (case_id,))
        
        if not result:
            raise HTTPException(404, "Case not found")
        
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(400, "No fields supplied")
        
        update_parts = []
        params = []
        
        field_mapping = {
            "title": "CaseDescription",
            "case_type": "CaseType",
            "status": "Status",
            "opened_date": "IncidentDate",
            "description": "CaseDescription"
        }
        
        for field, value in changes.items():
            if field in field_mapping:
                db_field = field_mapping[field]
                if field == "opened_date" and value:
                    try:
                        value = datetime.strptime(value, "%Y-%m-%d").date()
                    except:
                        value = datetime.now().date()
                update_parts.append(f"{db_field} = %s")
                params.append(value)
        
        if not update_parts:
            raise HTTPException(400, "No valid fields to update")
        
        params.append(case_id)
        update_query = f"UPDATE ForensicCase SET {', '.join(update_parts)} WHERE CaseID = %s"
        
        execute_query(update_query, params, fetch=False)
        
        add_audit("Updated Case", result[0]["CaseNumber"])
        
        return get_case(case_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in update_case: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

@app.delete("/api/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int):
    """Delete a case"""
    try:
        check_query = "SELECT CaseNumber FROM ForensicCase WHERE CaseID = %s"
        result = execute_query(check_query, (case_id,))
        
        if not result:
            raise HTTPException(404, "Case not found")
        
        tables_to_clear = [
            "Evidence", "Postmortem", "CourtReport", "Incident", "CaseCourt"
        ]
        
        for table in tables_to_clear:
            delete_related = f"DELETE FROM {table} WHERE CaseID = %s"
            execute_query(delete_related, (case_id,), fetch=False)
        
        delete_query = "DELETE FROM ForensicCase WHERE CaseID = %s"
        execute_query(delete_query, (case_id,), fetch=False)
        
        add_audit("Deleted Case", result[0]["CaseNumber"])
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"❌ Error in delete_case: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

# ==========================================
# Staff Endpoints
# ==========================================

@app.get("/api/staff")
def get_staff():
    """Get all staff members"""
    try:
        query = "SELECT * FROM Staff ORDER BY StaffID DESC"
        result = execute_query(query)
        
        if result is None:
            raise HTTPException(500, "Database query failed")
        
        formatted_result = []
        for row in result:
            formatted_result.append({
                "id": row.get("StaffID"),
                "employee_number": f"EMP-{row.get('StaffID')}",
                "full_name": row.get("StaffName") or "Unknown",
                "role": row.get("Role") or "Staff",
                "extension": "N/A",
                "duty_status": "On Duty",
                "shift": "Day"
            })
        return formatted_result
    except Exception as e:
        print(f"❌ Error in get_staff: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

# ==========================================
# Laboratory Endpoints
# ==========================================

@app.get("/api/laboratory")
def get_laboratory():
    """Get all laboratory tests"""
    try:
        query = "SELECT * FROM LaboratoryTest ORDER BY TestID DESC"
        result = execute_query(query)
        
        if result is None:
            raise HTTPException(500, "Database query failed")
        
        formatted_result = []
        for row in result:
            formatted_result.append({
                "id": row.get("TestID"),
                "request_number": f"LAB-{row.get('TestID')}",
                "sample_type": row.get("TestType") or "Unknown",
                "assigned_analyst": "Dr. Unknown",
                "status": "Completed" if row.get("Result") else "In Progress",
                "received_date": str(row.get("TestDate")) if row.get("TestDate") else None,
                "notes": row.get("Result") or "No results yet"
            })
        return formatted_result
    except Exception as e:
        print(f"❌ Error in get_laboratory: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

# ==========================================
# Resource Endpoints (Generic)
# ==========================================

@app.get("/api/{resource_name}")
def list_resource(resource_name: str):
    """Get resources from database based on resource name"""
    resource_mapping = {
        "laboratory": "LaboratoryTest",
        "court-reports": "CourtReport",
        "incidents": "Incident",
        "staff": "Staff",
        "audit-logs": "AuditLog"
    }
    
    if resource_name not in resource_mapping:
        raise HTTPException(404, "Resource not found")
    
    table_name = resource_mapping[resource_name]
    query = f"SELECT * FROM {table_name} ORDER BY {table_name}ID DESC"
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
                "assigned_analyst": "Dr. Unknown",
                "status": "Completed" if row.get("Result") else "In Progress",
                "received_date": str(row.get("TestDate")) if row.get("TestDate") else None,
                "notes": row.get("Result") or "No results yet"
            })
        else:
            formatted_result.append(row)
    
    return formatted_result

# ==========================================
# Dynamic Pages
# ==========================================

@app.get("/api/pages/{page_id}", response_class=HTMLResponse)
def dynamic_page(page_id: str):
    """Generate dynamic pages from database data"""
    if page_id in {"about_us", "contact_us"}:
        page_path = FRONTEND_DIR / "pages" / f"{page_id}.html"
        if page_path.exists():
            return page_path.read_text(encoding="utf-8")
        return page_heading(page_id.replace("_", " ").title(), "<p>Page content not found.</p>")
    
    if page_id == "cases":
        query = "SELECT * FROM ForensicCase ORDER BY CaseID DESC LIMIT 20"
        cases = execute_query(query) or []
        
        cards = "".join(f'<div style="background:#fffdf5;border:1px solid #e0dacb;padding:15px;margin-bottom:8px;"><strong>{esc(row["CaseDescription"][:50] if row["CaseDescription"] else "Untitled")} – {esc(row["CaseNumber"])}</strong><p style="margin:8px 0;font-size:13px;">Status: {esc(row["Status"])} | Type: {esc(row["CaseType"])}</p><button onclick="showCase({row["CaseID"]})" style="background:#004488;color:white;border:0;padding:6px 15px;cursor:pointer;">View Case</button></div>' for row in cases)
        return page_heading("Active Forensic Cases & Applications", cards or "<p>No cases found.</p>")
    
    if page_id == "laboratory":
        query = "SELECT * FROM LaboratoryTest ORDER BY TestID DESC"
        tests = execute_query(query) or []
        
        body = "".join(f'<tr><td>LAB-{esc(str(row["TestID"]))}</td><td>{esc(row["TestType"])}</td><td>Analyst</td><td><strong>{esc("Completed" if row["Result"] else "In Progress")}</strong></td></tr>' for row in tests)
        return page_heading("Laboratory Services", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Request ID</th><th>Sample Type</th><th>Assigned Analyst</th><th>Status</th></tr>{body}</table>')
    
    if page_id == "staff":
        query = "SELECT * FROM Staff ORDER BY StaffID DESC"
        staff = execute_query(query) or []
        
        lis = "".join(f'<li><strong>{esc(row["Role"])}:</strong> {esc(row["StaffName"])} — {esc(row["ContactNo"])}</li>' for row in staff)
        return page_heading("Staff & Duty Roster", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;"><ul>{lis}</ul></div>')
    
    if page_id == "audit_logs":
        query = "SELECT * FROM AuditLog ORDER BY AuditID DESC LIMIT 50"
        logs = execute_query(query) or []
        
        body = "".join(f'<tr><td>{esc(str(row["ActionDate"]) if row["ActionDate"] else "N/A")}</td><td>User {esc(str(row["UserID"]))}</td><td>{esc(row["Action"])}</td><td>Resource</td></tr>' for row in logs)
        return page_heading("System Audit Logs", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Timestamp</th><th>User</th><th>Action</th><th>Resource</th></tr>{body}</table>')
    
    raise HTTPException(404, "Page not found")

# ==========================================
# Frontend Routes
# ==========================================

@app.get("/")
def frontend() -> FileResponse:
    """Serve the main frontend page"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Forensa - Forensic Medical System</h1><p>Frontend not found. Please check the directory structure.</p>")

# Mount static files
app.mount("/pages", StaticFiles(directory=FRONTEND_DIR / "pages"), name="pages")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ==========================================
# Main Entry Point
# ==========================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🌐 Starting server at http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)