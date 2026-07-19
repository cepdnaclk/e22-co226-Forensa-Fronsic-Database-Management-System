import sys

# Add repository root to python search path
sys.path.append(r"c:\Users\ASUS\project_forensa")

from Code.backend.app import dynamic_page

try:
    # Try calling the dynamic_page function directly in Python
    html = dynamic_page("incidents", "Bearer mock-token-lab_mary")
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
