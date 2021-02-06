"""
Widget that manages & displays the list of scenes and editable shader sections in each scene.
"""
from util import *
import icons
import os
from send2trash import send2trash
from multiplatformutil import selectInFileBrowser, openFileWithDefaultApplication


class MimeDataItemModel(QStandardItemModel):
    def mimeData(self, modelIndices):
        data = []
        for index in modelIndices:
            if index.isValid():
                data.append(index.data())
        mimeData = QMimeData()
        mimeData.setText(';'.join(data))
        return mimeData


class SceneList(QWidget):
    currentChanged = pyqtSignal(QStandardItem)
    requestCreateShot = pyqtSignal(str)

    def __init__(self):
        super(SceneList, self).__init__()

        self.__shotsManager = None

        main = vlayout()
        self.setLayout(main)
        belt = hlayout()

        addScene = QPushButton(icons.get('Add Image-48'), '')
        addScene.clicked.connect(self.__onAddScene)
        addScene.setIconSize(QSize(24, 24))
        addScene.setToolTip('Add scene')
        addScene.setStatusTip('Add scene')
        belt.addWidget(addScene)

        delScene = QPushButton(icons.get('Remove Image-48'), '')
        delScene.clicked.connect(self.__onDeleteScene)
        delScene.setIconSize(QSize(24, 24))
        delScene.setToolTip('Delete scene')
        delScene.setStatusTip('Delete scene')
        belt.addWidget(delScene)

        belt.addStretch(1)
        main.addLayout(belt)
        self.__model = MimeDataItemModel()
        self.view = QTreeView()
        self.view.setModel(self.__model)
        self.view.activated.connect(self.__onOpenFile)
        self.view.setEditTriggers(self.view.NoEditTriggers)
        main.addWidget(self.view)
        main.setStretch(1, 1)
        self.view.selectionModel().currentChanged.connect(self.__onCurrentChanged)

        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.__contextMenu)
        self.contextMenu = QMenu()
        action = self.contextMenu.addAction('Show in explorer')
        action.triggered.connect(self.__showInExplorer)
        action = self.contextMenu.addAction('Create shot')
        action.triggered.connect(self.__createShot)
        self.__contextMenuItem = None

    def selectSceneWithName(self, name):
        items = self.view.model().findItems(name)
        if items:
            self.view.setExpanded(items[0].index(), True)
            self.view.selectionModel().select(items[0].index(), QItemSelectionModel.ClearAndSelect)

    def __showInExplorer(self):
        if self.__contextMenuItem is None:
            return
        data = self.__contextMenuItem.data()
        assert data is None or isinstance(data, FilePath)
        if not data or not data.exists():
            # try navigation by file name
            data = currentScenesDirectory().join(self.__contextMenuItem.text())
        if not data or not data.exists():
            return
        selectInFileBrowser(data)

    def __createShot(self):
        for idx in self.view.selectionModel().selectedIndexes():
            item = self.view.model().itemFromIndex(idx)
            self.requestCreateShot.emit(item.text())
            return

    def __contextMenu(self, pos):
        index = self.view.indexAt(pos)
        if not index.isValid():
            return
        item = self.view.model().itemFromIndex(index)
        self.__contextMenuItem = item
        self.contextMenu.popup(self.view.mapToGlobal(pos))

    def setShotsManager(self, manager):
        self.__shotsManager = manager

    def __onOpenFile(self, current):
        if not current.parent().isValid():
            return
        path = FilePath(self.view.model().itemFromIndex(current).data())
        openFileWithDefaultApplication(path)

    def __onCurrentChanged(self, current, __):
        if not current.parent().isValid():
            self.currentChanged.emit(self.view.model().itemFromIndex(current))

    @property
    def model(self):
        return self.view.model()

    def projectOpened(self):
        self.setEnabled(True)
        self.clear()
        self.initShared()
        for scene in iterSceneNames():
            self.appendSceneItem(scene)

    def __onDeleteScene(self):
        if QMessageBox.warning(self, 'Deleting scene', 'This action is not undoable! Continue?', QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        rows = []
        for idx in self.view.selectionModel().selectedIndexes():
            rows.append(idx.row())
            item = self.view.model().itemFromIndex(idx)
            sceneName = str(item.text())
            self.__shotsManager.onDeleteScene(sceneName)
            sceneDir = currentScenesDirectory().join(sceneName)
            sceneFile = sceneDir + SCENE_EXT
            send2trash(sceneFile)
            send2trash(sceneDir)
        rows.sort()
        for row in rows[::-1]:
            self.view.model().removeRow(row)

    def __onAddScene(self):
        # request user for a template if there are multiple options
        templates = list(iterTemplateNames())

        if not templates:
            QMessageBox.critical(self, 'Could not create scene', 'Can not add scenes to this project until a template has been made to base them off.')
            return

        if len(templates) == 1:
            templateDir = templateFolderFromName(templates[0])
            templatePath = templateFileFromName(templates[0])
        else:
            template = QInputDialog.getItem(self, 'Create scene', 'Select template', templates, 0, False)
            if not template[1] or not template[0] in templates:
                return
            templateDir = templateFolderFromName(template[0])
            templatePath = templateFileFromName(template[0])

        name = QInputDialog.getText(self, 'Create scene', 'Scene name')
        if not name[1]:
            return

        scenesPath = currentScenesDirectory()
        outFile = scenesPath.join(name[0] + SCENE_EXT)
        outDir = scenesPath.join(name[0])
        if outFile.exists():
            QMessageBox.critical(self, 'Could not create scene', 'A scene with name "%s" already exists. No scene was created.' % name[0])
            return

        if outDir.exists():
            if QMessageBox.Cancel == QMessageBox.warning(self, 'Scene not empty', 'A folder with name "%s" already exists. Create scene anyways?' % name[0], QMessageBox.Ok | QMessageBox.Cancel):
                return
        else:
            outDir.ensureExists(True)

        with outFile.edit() as fh:
            fh.write('<scene camera="0,1,-10,0,0,0" template="%s"/>' % os.path.relpath(templatePath, scenesPath))

        # find required template inputs (sections)
        xTemplate = parseXMLWithIncludes(templatePath)
        for xPass in xTemplate:
            for xElement in xPass:
                if xElement.tag.lower() != 'section':
                    continue
                # given a section make a stub file so the scene is complete on disk
                resource = templateDir.join(xElement.attrib['path'])
                # copy template data if there is any
                text = resource.content() if resource.exists() else ''
                with outDir.join(xElement.attrib['path']).edit() as fh:
                    fh.write(text)

        self.appendSceneItem(name[0])

    def initShared(self):
        for templateName in iterTemplateNames():
            item = QStandardItem(':' + templateName)

            # grab unique shared items
            sharedPaths = set(sharedPathsFromTemplate(templateName))

            # order alphabetically (case insensitive)
            sharedPaths = sorted(sharedPaths, key=lambda path: path.name().lower())

            # add to model
            for path in sharedPaths:
                sub = QStandardItem(path.name())
                sub.setData(path)
                item.appendRow(sub)

            if item.rowCount():
                self.view.model().appendRow(item)

    def appendSceneItem(self, sceneName):
        item = QStandardItem(sceneName)
        self.view.model().appendRow(item)

        # grab unique items
        sectionPaths = set(sectionPathsFromScene(sceneName))

        # order alphabetically (case insensitive)
        sectionPaths = sorted(sectionPaths, key=lambda path: path.name().lower())

        # add to model
        for path in sectionPaths:
            sub = QStandardItem(path.name())
            sub.setData(path)
            item.appendRow(sub)

    def clear(self):
        self.view.model().clear()
