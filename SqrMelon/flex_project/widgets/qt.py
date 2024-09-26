from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class DoubleEdit(QDoubleSpinBox):
    def __init__(self, value=0.0):
        super().__init__()
        self.setMinimum(-float('inf'))
        self.setMaximum(float('inf'))
        self.setSingleStep(0.01)
        self.setValue(value)
