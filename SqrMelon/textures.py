from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import icons
from fileutil import FileDialog
from projutil import currentProjectDirectory
from qt import *
from qtutil import hlayout, vlayout

if TYPE_CHECKING:
    from shots import Shot


class TextureManager(QDialog):
    """
    Utility to manage textures per camera shot.
    Not supported by the runtime but useful for mockups and animatics during the concept phase.
    """

    def __init__(self, target: Shot, parent: Optional[QWidget] = None) -> None:
        super(TextureManager, self).__init__(parent)

        self.setWindowTitle('TextureManager')

        main = vlayout()
        self.setLayout(main)

        belt = hlayout()
        main.addLayout(belt)

        addImage = QPushButton(icons.get('Add Image-48'), '')
        addImage.clicked.connect(self.__onAddImage)
        addImage.setIconSize(QSize(24, 24))
        addImage.setToolTip('Add texture')
        addImage.setStatusTip('Add texture')
        belt.addWidget(addImage)

        delImage = QPushButton(icons.get('Remove Image-48'), '')
        delImage.clicked.connect(self.__onDeleteImages)
        delImage.setIconSize(QSize(24, 24))
        delImage.setToolTip('Delete selected images')
        delImage.setStatusTip('Delete selected images')
        belt.addWidget(delImage)

        belt.addStretch(1)

        self.__model = QStandardItemModel()
        self.__view = QTableView()
        self.__view.setModel(self.__model)
        self.__view.horizontalHeader().hide()
        self.__view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.__view.verticalHeader().hide()
        main.addWidget(self.__view)
        main.setStretch(1, 1)

        self.__target = target
        for uniformName in target.textures:
            relPath = target.textures[uniformName]
            nameItem = QStandardItem(uniformName)
            nameItem.setIcon(QIcon(currentProjectDirectory().join(relPath)))
            pathItem = QStandardItem(relPath)
            pathItem.setFlags(pathItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.__model.appendRow([nameItem, pathItem])

    def __onAddImage(self) -> None:
        uniformName_ = QInputDialog.getText(self, 'Add texture', 'Uniform name', QLineEdit.EchoMode.Normal, 'uTextures[0]')
        if not uniformName_[0] or not uniformName_[1]:
            return
        uniformName = uniformName_[0]

        imagePath = FileDialog.getOpenFileName(self, currentProjectDirectory(), '', 'Image files (*.png;*.bmp;*.jpg;*.jpeg;*.tiff);;Raw Gray F32 map (*.r32)')
        if imagePath and imagePath.exists():
            relPath = imagePath.relativeTo(currentProjectDirectory())
            self.__target.textures[uniformName] = relPath

            nameItem = QStandardItem(uniformName)
            nameItem.setIcon(QIcon(imagePath))
            pathItem = QStandardItem(relPath)
            pathItem.setFlags(pathItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.__model.appendRow([nameItem, pathItem])

    def __onDeleteImages(self) -> None:
        rows = []

        for idx in self.__view.selectedIndexes():
            rows.append(idx.row())

        for row in reversed(sorted(rows)):
            name = self.__model.item(row, 0)
            if not name:
                continue
            del self.__target.textures[str(name.text())]
            self.__model.takeRow(row)
