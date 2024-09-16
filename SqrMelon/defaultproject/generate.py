import os
from pathlib import Path
import subprocess
import sys

ERR_SQRMELON_NOT_FOUND = 1000

# Read SqrMelon last used installment.
sharedDir = Path(os.getenv('ProgramData', 'C:\\ProgramData')) if os.name == 'nt' else Path('/usr/local/share')
sharedDir.mkdir(parents = True, exist_ok = True)
sqrMelonDir = None
with open(sharedDir / "SqrMelon-InstallDir.txt", 'r') as file:
    sqrMelonDir = file.readline()
if sqrMelonDir is not None:
    sqrMelonDir = sqrMelonDir.strip()
else:
    print("ERR: no SqrMelon installment was found.")
    exit(ERR_SQRMELON_NOT_FOUND)

# Run SqrMelon/generate.py.
try:
    subprocess.run([ 
        sys.executable, 
        Path(os.path.join(sqrMelonDir, "generate.py")).__str__(), 
        Path(os.path.dirname(os.path.abspath(__file__))).__str__()                    
    ], check = True, capture_output = False, text = True)
except:
    pass
