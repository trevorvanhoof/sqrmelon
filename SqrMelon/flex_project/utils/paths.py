import os
from pathlib import Path


def canonicalAbsolutepath(path: str) -> str:
    # Allow %VAR%.
    path = os.path.expandvars(path)
    # Resolve links and dots.
    path = os.path.realpath(path)
    # Request actual case from system, should only do something on Windows.
    return str(Path(path).resolve())
