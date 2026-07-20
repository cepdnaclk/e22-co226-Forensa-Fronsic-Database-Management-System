___
# DELETE THIS INSTRUCTIONS AND ADD A SHORT INTRODUCTION ABOUT YOUR PROJECT
___

## Please refer the instructions in below URL:

https://projects.ce.pdn.ac.lk/docs/how-to-add-a-project
# Setup Guide

## Prerequisites

Before running the project, install:

- Python 3.10 or later
- MySQL Server
- MySQL Workbench (optional)

---

## 1. Clone the Repository

```bash
git clone https://github.com/cepdnaclk/project_forensa.git
cd project_forensa
```

---

## 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the virtual environment (Windows):

```bash
.venv\Scripts\activate
```

---

## 3. Install Required Python Packages

```bash
pip install -r Code/backend/requirements.txt
```

If required, install the following packages manually:

```bash
pip install mysql-connector-python python-dotenv pytest httpx
```

---

## 4. Set Up the Database

Create a MySQL database:

```sql
CREATE DATABASE ForensicMedicalDB;
```

Run the SQL scripts in this order:

1. `database/01. Table_Creation.sql`
2. `database/02. Data_Insertion.sql`

---

## 5. Configure Environment Variables

Create a `.env` file inside the `Code/backend` folder.

Example:

```env
DB_HOST=localhost
DB_NAME=ForensicMedicalDB
DB_USER=root
DB_PASSWORD=your_password
DB_PORT=3306
```

---

## 6. Run the Backend & Frontend

From the project root directory:

```bash
run_backend.bat
```

or

```bash
python backend/app.py
```

---

## 7. Run API Tests

Run the complete test suite with `pytest`:

```bash
pytest Code/backend/tests -v
```

or directly using the virtual environment executable:

```bash
.\.venv\Scripts\pytest.exe Code/backend/tests -v
```

To run a specific test file:

```bash
pytest Code/backend/tests/test_auth.py -v
```

---

## Technologies Used

- Python
- FastAPI
- MySQL
- MySQL Connector/Python
- python-dotenv
- Pytest & HTTPX
