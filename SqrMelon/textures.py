import os
from util import ProjectDir
from qtutil import *
import icons


class TextureManager(QDialog):
    """
    Utility to manage textures per camera shot.
    Not supported by the runtime but useful for mockups and animatics during the concept phase.
    """
    def __init__(self, target, parent=None):
        super(TextureManager, self).__init__(parent)

        self.setWindowTitle('TextureManager')

        main = vlayout()
        self.setLayout(main)

        belt = hlayout()
        main.addLayout(belt)

        addImage = QPushButton(icons.get('Add Image'), '')
        addImage.clicked.connect(self.__onAddImage)
        addImage.setIconSize(QSize(24, 24))
        addImage.setToolTip('Add texture')
        addImage.setStatusTip('Add texture')
        belt.addWidget(addImage)

        delImage = QPushButton(icons.get('Remove Image'), '')
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
        self.__view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.__view.verticalHeader().hide()
        main.addWidget(self.__view)
        main.setStretch(1, 1)

        self.__target = target
        for uniformName in target.textures:
            relPath = target.textures[uniformName]
            nameItem = QStandardItem(uniformName)
            nameItem.setIcon(QIcon(os.path.join(ProjectDir(), relPath)))
            pathItem = QStandardItem(relPath)
            pathItem.setFlags(pathItem.flags() & ~Qt.ItemIsEditable)
            self.__model.appendRow([nameItem, pathItem])

    def __onAddImage(self):
        uniformName = QInputDialog.getText(self, 'Add texture', 'Uniform name', QLineEdit.Normal, 'uTextures[0]')
        if not uniformName[0] or not uniformName[1]:
            return
        uniformName = uniformName[0]

        imagePath = QFileDialog.getOpenFileName(self, ProjectDir(), '', 'Image files (*.png;*.bmp;*.jpg;*.jpeg;*.tiff);;Raw Gray F32 map (*.r32)')
        if imagePath and os.path.exists(imagePath):
            relPath = os.path.relpath(imagePath, ProjectDir())
            self.__target.textures[uniformName] = relPath

            nameItem = QStandardItem(uniformName)
            nameItem.setIcon(QIcon(imagePath))
            pathItem = QStandardItem(relPath)
            pathItem.setFlags(pathItem.flags() & ~Qt.ItemIsEditable)
            self.__model.appendRow([nameItem, pathItem])

    def __onDeleteImages(self):
        rows = []

        for idx in self.__view.selectedIndexes():
            rows.append(idx.row())

        for row in reversed(sorted(rows)):
            name = self.__model.item(row, 0)
            if not name:
                continue
            del self.__target.textures[str(name.text())]
            self.__model.takeRow(row)
