import sys
import os
import tempfile

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import web_app

# Use temporary file for CSV writes during tests to keep production dataset clean
test_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
test_csv.close()
web_app.CSV_PATH = test_csv.name
