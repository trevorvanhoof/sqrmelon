# simple script to delete all saved settings (about window layout, recent projects, etc)
from PyQt4.QtCore import *
s = QSettings('PB', 'Py64k')
for key in s.allKeys(): s.remove(key)
