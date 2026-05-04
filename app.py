"""
Streamlit Cloud entrypoint shim.

Streamlit Cloud is configured to run app.py at the repo root.
The real app lives at frontend/app.py — this file delegates to it.

To change the entrypoint to frontend/app.py directly, update the
"Main file path" in the Streamlit Cloud app dashboard and delete this file.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_entry = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "app.py")
with open(_entry) as _fh:
    exec(compile(_fh.read(), _entry, "exec"))
