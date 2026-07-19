import urllib.request
import json
import sys

def get_req(url, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return res.getcode(), res.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.reason

def post_json(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return res.getcode(), json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.reason

# 1. Login to get token for lab_mary (Lab Technician)
print("1. Logging in lab_mary (Lab Technician)...")
code, login_mary = post_json('http://127.0.0.1:8000/api/auth/login', {
    'username': 'lab_mary',
    'password': 'password123'
})
token_mary = login_mary.get('token')
print(f"Lab Tech Token: {token_mary}")

# 2. Verify lab_mary is allowed to access page 'incidents'
print("\n2. Checking page 'incidents' access...")
status, _ = get_req("http://127.0.0.1:8000/api/pages/incidents", token=token_mary)
print(f"Page 'incidents': {status} (Expected: 200)")
if status != 200:
    print("FAILED: Lab Tech should now be allowed to view page 'incidents'")
    sys.exit(1)

# 3. Verify lab_mary is allowed to list resource 'incidents'
print("\n3. Checking resource 'incidents' query access...")
status, _ = get_req("http://127.0.0.1:8000/api/incidents", token=token_mary)
print(f"Resource 'incidents': {status} (Expected: 200)")
if status != 200:
    print("FAILED: Lab Tech should now be allowed to query resource 'incidents'")
    sys.exit(1)

# 4. Verify lab_mary can create a new incident associated with case ID 1
print("\n4. Creating a new incident as lab_mary...")
code, new_inc = post_json('http://127.0.0.1:8000/api/incidents', {
    'case_id': 1,
    'incident_type': 'Crime Scene Lab Dispatch',
    'location': 'Colombo 07',
    'police_station': 'Cinnamon Gardens',
    'description': 'Lab tech dispatch for chemical analysis.',
    'incident_date': '2026-07-19'
}, token=token_mary)
print(f"Status: {code}, Response: {new_inc}")

if code != 201:
    print("FAILED: Lab Tech was unable to create an incident.")
    sys.exit(1)

print("\nSUCCESS! Lab Technicians are fully authorized to manage incidents.")
