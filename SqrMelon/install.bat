if exist %USERPROFILE%/Downloads/python-2.7.15.amd64.msi (
    rem file exists
) else (
bitsadmin.exe /transfer "Downloading python 2.7.15" https://www.python.org/ftp/python/2.7.15/python-2.7.15.amd64.msi %USERPROFILE%/Downloads/python-2.7.15.amd64.msi
)
start /wait msiexec.exe /i "%USERPROFILE%\Downloads\python-2.7.15.amd64.msi" /QN /L*V "C:\msilog.txt" MaintenanceForm_Action=Repair
if exist %USERPROFILE%/Downloads/PyQt4-4.11.4-gpl-Py2.7-Qt4.8.7-x64.exe (
    rem file exists
) else (
bitsadmin.exe /transfer "Downloading PyQt4.11.4" https://kent.dl.sourceforge.net/project/pyqt/PyQt4/PyQt-4.11.4/PyQt4-4.11.4-gpl-Py2.7-Qt4.8.7-x64.exe %USERPROFILE%/Downloads/PyQt4-4.11.4-gpl-Py2.7-Qt4.8.7-x64.exe 
)
call update.bat
%USERPROFILE%/Downloads/PyQt4-4.11.4-gpl-Py2.7-Qt4.8.7-x64.exe
