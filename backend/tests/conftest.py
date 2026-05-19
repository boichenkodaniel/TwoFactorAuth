import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.resolve()

sys.path.insert(0, str(BACKEND_DIR))

os.chdir(BACKEND_DIR)
