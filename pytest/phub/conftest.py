import pathlib
import sys


# Ensure the project root is on sys.path for test imports without installation.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
