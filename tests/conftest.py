import os
os.environ.setdefault("TYPEMASTER_SPLASH", "0")
import os
import sys
import tempfile
from pathlib import Path

# Must be set before any typemaster module is imported.
os.environ.setdefault("TYPEMASTER_DB", str(Path(tempfile.mkdtemp()) / "app-test.db"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
