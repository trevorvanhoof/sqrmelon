# PRE-REQUIREMENTS
# * Either "%PROGRAMDATA%/SqrMelon-InstallDir.txt" (Windows) or 
#   "/usr/local/share/SqrMelon-InstallDir.txt" (other systems) should exist.
#   That file is created when running SqrMelon and contents refer to the
#   directory where SqrMelon is located.

# HOW IT WORKS
# * Project directory is locked to ensure no concurrent processes are run.
# * SqrMelon-InstallDir.txt is loaded to determine the SqrMelon installment.
# * Project filename is resolved.
# * MelonPan is either installed or upgraded to the project folder (only if
#   "__customplayer.txt" file is not present). Content folder is copied but
#   never updated.
# * Scenes and Templates are copied to (PROJECTDIR)/MelonPan/content.
# * If exists, userland (PROJECTDIR)/__custompregeneratestep.py is run.
# * The harvester is run on (PROJECTDIR)/MelonPan/content.
# * Project directory is unlocked.

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ERR_MISSING_PROJECT_FILE = 1001
ERR_ANOTHER_INSTANCE_RUNNING = 1002
ERR_PREGENERATESTEP_TERMINATED_WITH_ERRORS = 1003
ERR_HARVESTER_TERMINATED_WITH_ERRORS = 1004
ERR_MISSING_PROJECT_DIR = 1005
ERR_UNKNOWN_ERROR = 9999
PROJ_EXT = '.p64'
CUSTOMPREGENERATESTEP_FILENAME = "__custompregeneratestep.py"

def __copyPlayerFileIfHonored(src: Path, dst: Path) -> None:
    """
    If src is a directory:
        * Create it.
    If src is a file:
        * If the file does not exist in dst, copy it.
        * If the file does exist in dst:
            * If the file is not under "content", last modification date differ or content differ, overwrite it.
    """
    def md5FromFile(filepath: Path) -> str:
        md5Stream = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5Stream.update(chunk)
        return md5Stream.hexdigest()

    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
    else:
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok = True)
            shutil.copy2(src, dst)
        else:
            if os.path.basename(os.path.dirname(src)) != 'content':
                if (os.path.getmtime(src) != os.path.getmtime(dst)) or (md5FromFile(src) != md5FromFile(dst)):
                    shutil.copy2(src, dst)

def __unlockAndExit(lockFile: Path, errorMsg: str, exitCode: int) -> None:
    """
    Remove the global lock file, print error message and quit with exit code.
    """
    if os.path.exists(lockFile):
        os.remove(lockFile)
    print("\n" + errorMsg)
    exit(exitCode)

def __tryRunPythonScript(cmdLineItems: list) -> tuple[int, str]:
    """
    If first item in cmdLineItems represents a Python script file that exists in the filesystem, runs it using the rest of
    items in cmdLineItems as arguments. The interpreter used is the same running this file.
    """
    result = None
    if os.path.exists(cmdLineItems[0]):
        try:
            result = subprocess.run([ sys.executable ] + cmdLineItems, check = True, capture_output = True, text = True)
            return [ 1, result.stdout ]
        except subprocess.CalledProcessError as e: 
            return [ 0, e.stdout + e.stderr ]
    else:
        return [ -1, '' ]

def __syncDstDirWithSrcDir(src: str, dst: str) -> None:
    """
    Synchronize contents of destination with source by deleting files and directories in destination not present in source.
    """    
    assert os.path.isdir(src)
    assert os.path.isdir(dst)

    for item in (set(os.listdir(dst)) - set(os.listdir(src))):
        path = os.path.join(dst, item)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except:
            pass

def __generate(projectDir: str, lockFile: str) -> None:
    # Lock or die.
    try:
        with open(lockFile, 'x') as file:
            pass
    except FileExistsError:
        print("ERR: Another instance is running.")
        exit(ERR_ANOTHER_INSTANCE_RUNNING)

    sqrMelonDir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Find project file.
    projectFile = None
    allProjectFiles = [p for p in list(os.listdir(projectDir)) if p and p.endswith(PROJ_EXT)]
    if allProjectFiles:
        projectFile = allProjectFiles[0]
    if projectFile is None:
        __unlockAndExit(lockFile, "ERR: No SqrMelon project file was found in current directory.", ERR_MISSING_PROJECT_FILE)
    print("INF: Building project " + projectFile + ".")

    # Install or upgrade MelonPan if required.
    customPlayerFlagFilePath = Path(os.path.join(projectDir, '__customplayer.txt'))
    melonPanDir = None
    ignoreHiddenDirectories = lambda src, names: [name for name in names if os.path.isdir(os.path.join(src, name)) and name.startswith('.')]
    if not customPlayerFlagFilePath.exists():
        src = os.path.abspath(os.path.join(sqrMelonDir, "../MelonPan")).replace("\\", "/")
        melonPanDir = dst = os.path.abspath(os.path.join(projectDir, "MelonPan")).replace("\\", "/")
        print("INF: Updating local MelonPan installment: " + src + " -> " + dst + "...", end = '')
        shutil.copytree(src, dst, False, ignoreHiddenDirectories, __copyPlayerFileIfHonored, False, True)
        print("OK")
    else:
        print("INF: Using custom player, no update will take place.")

    # Copy or upgrade project files to MelonPan/content.
    contentPaths = {}
    for f in [ "Scenes", "Templates", projectFile ]:
        src = os.path.join(projectDir, f).replace("\\", "/")
        dst = os.path.join(melonPanDir, "content", f).replace("\\", "/")
        print("INF: Copying " + f + " to content directory...", end = '')
        if (os.path.isfile(src)):
            __copyPlayerFileIfHonored(src, dst)
        else:
            # Copy the fs tree.
            shutil.copytree(src, dst, False, ignoreHiddenDirectories, __copyPlayerFileIfHonored, False, True)
            # Remove files no longer referenced by the project.
            __syncDstDirWithSrcDir(src, dst)

        contentPaths[f] = dst
        print("OK")

    # Run the custom pregenerate step script, if exists.
    processResult = __tryRunPythonScript([ os.path.join(projectDir, CUSTOMPREGENERATESTEP_FILENAME), contentPaths["Templates"], contentPaths["Scenes"] ])
    match processResult[0]:
        case  0:
            __unlockAndExit(lockFile, "ERR: Custom pregenerate step script " + CUSTOMPREGENERATESTEP_FILENAME + " failed. Output:\n" + processResult[1], ERR_PREGENERATESTEP_TERMINATED_WITH_ERRORS)
        case  1:
            print("INF: Pregenerate step script " + CUSTOMPREGENERATESTEP_FILENAME + " run.")

    # Run the harvester.
    print("INF: Harvesting data...", end = '')
    processResult = __tryRunPythonScript([ os.path.join(sqrMelonDir, "harvester.py"), os.path.join(melonPanDir, "content", projectFile).replace("\\", "/"), melonPanDir.replace("\\", "/") ])
    match processResult[0]:
        case  0:
            __unlockAndExit(lockFile, "ERR: Harvester failed. Output:\n" + processResult[1], ERR_HARVESTER_TERMINATED_WITH_ERRORS)
        case  1:
            print("OK")
        case -1:
            __unlockAndExit(lockFile, "ERR: Harvester was not found.", ERR_HARVESTER_TERMINATED_WITH_ERRORS)

    print("INF: Your project is ready to build!")            

    # Unlock.
    if os.path.exists(lockFile):
        os.remove(lockFile)

try:
    if len(sys.argv) < 2:
        print("ERR: No project directory was given as argument.")
        exit(ERR_MISSING_PROJECT_DIR)

    projectDir = os.path.abspath(sys.argv[1])
    lockFile = os.path.join(projectDir, ".lock")
    __generate(projectDir, lockFile)
    
except Exception as e:
    print()
    exc_type, exc_value, exc_traceback = sys.exc_info()
    __unlockAndExit(lockFile, "ERR: Unknown exception:\n" + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), ERR_UNKNOWN_ERROR)
