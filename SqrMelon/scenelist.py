"""
Widget that manages & displays the list of scenes and editable shader sections in each scene.
"""
import fileutil
from util import *
import icons
from send2trash import send2trash
import subprocess


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

    def __init__(self, subFolder=''):
        """"
        @param subFolder: make this scene list represent a "Scenes, Templates"
        folder pair in a sub-folder instead of the project root.
        """
        super(SceneList, self).__init__()

        self.__subFolder = subFolder
        self.__shotsManager = None

        main = vlayout()
        self.setLayout(main)
        belt = hlayout()

        addScene = QPushButton(icons.get('Add Image'), '')
        addScene.clicked.connect(self.__onAddScene)
        addScene.setIconSize(QSize(24, 24))
        addScene.setToolTip('Add scene')
        addScene.setStatusTip('Add scene')
        belt.addWidget(addScene)

        delScene = QPushButton(icons.get('Remove Image'), '')
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
        if not data or not fileutil.exists(data):
            data = os.path.join(ScenesPath(), self.__contextMenuItem.text())
        if not data or not fileutil.exists(data):
            return
        data = os.path.abspath(data)
        subprocess.Popen('explorer /select,"%s"' % data)

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
        path = self.__model.itemFromIndex(current).data()
        os.startfile(path.replace('\\', '/'))

    def __onCurrentChanged(self, current, __):
        if not current.parent().isValid():
            self.currentChanged.emit(self.__model.itemFromIndex(current))

    @property
    def model(self):
        return self.__model

    def projectOpened(self):
        self.setEnabled(True)
        self.clear()
        self.initShared()
        for scene in Scenes(self.__subFolder):
            self.appendSceneItem(os.path.splitext(scene)[0])

    def __onDeleteScene(self):
        if QMessageBox.warning(self, 'Deleting scene', 'This action is not undoable! Continue?', QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        rows = []
        for idx in self.view.selectionModel().selectedIndexes():
            rows.append(idx.row())
            item = self.__model.itemFromIndex(idx)
            sceneName = str(item.text())
            self.__shotsManager.onDeleteScene(sceneName)
            sceneDir = os.path.join(ScenesPath(), sceneName)
            sceneFile = sceneDir + SCENE_EXT
            send2trash(sceneFile)
            send2trash(sceneDir)
        rows.sort()
        for row in rows[::-1]:
            self.__model.removeRow(row)

    def __onAddScene(self):
        # request user for a template if there are multiple options
        templates = list(Templates(self.__subFolder))

        if not templates:
            QMessageBox.critical(self, 'Could not create scene', 'Can not add scenes to this project until a template has been made to base them off.')
            return

        if len(templates) == 1:
            templateDir = TemplateSourceFolderFromName(templates[0], self.__subFolder)
            templatePath = TemplateFileFromName(templates[0], self.__subFolder)
        else:
            template = QInputDialog.getItem(self, 'Create scene', 'Select template', templates, 0, False)
            if not template[1] or not template[0] in templates:
                return
            templateDir = TemplateSourceFolderFromName(template[0], self.__subFolder)
            templatePath = TemplateFileFromName(template[0], self.__subFolder)

        name = QInputDialog.getText(self, 'Create scene', 'Scene name')
        if not name[1]:
            return

        scenesPath = ScenesPath(self.__subFolder)
        outFile = os.path.join(scenesPath, name[0] + SCENE_EXT)
        outDir = os.path.join(scenesPath, name[0])
        if fileutil.exists(outFile):
            QMessageBox.critical(self, 'Could not create scene', 'A scene with name "%s" already exists. No scene was created.' % name[0])
            return

        if fileutil.exists(outDir):
            if QMessageBox.warning(self, 'Scene not empty', 'A folder with name "%s" already exists. Create scene anyways?' % name[0], QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
        else:
            os.makedirs(outDir.replace('\\', '/'))

        with fileutil.edit(outFile) as fh:
            fh.write('<scene camera="0,1,-10,0,0,0" template="%s"/>' % os.path.relpath(templatePath, scenesPath))

        # find required template inputs (sections)
        xTemplate = ParseXMLWithIncludes(templatePath)
        for xPass in xTemplate:
            for xElement in xPass:
                if xElement.tag.lower() != 'section':
                    continue
                # given a section make a stub file so the scene is complete on disk
                resource = os.path.join(templateDir, xElement.attrib['path'])
                text = ''
                # copy template data if there is any
                if fileutil.exists(resource):
                    with fileutil.read(resource) as fh:
                        text = fh.read()
                with fileutil.edit(os.path.join(outDir, xElement.attrib['path'])) as fh:
                    fh.write(text)

        self.appendSceneItem(name[0])

    def initShared(self):
        for templateName in Templates():
            item = QStandardItem(':' + templateName)

            filtered = {path.lower(): path for path in sharedPathsFromTemplate(templateName, self.__subFolder)}
            allPaths = (filtered[key] for key in sorted(filtered.keys()))

            for path in allPaths:
                name = os.path.splitext(os.path.basename(path))[0]
                sub = QStandardItem(name)
                sub.setData(path)
                item.appendRow(sub)
            if item.rowCount():
                self.__model.appendRow(item)

    def appendSceneItem(self, sceneName):
        item = QStandardItem(sceneName)
        self.__model.appendRow(item)

        filtered = {path.lower(): path for path in sectionPathsFromScene(sceneName, self.__subFolder)}
        allPaths = (filtered[key] for key in sorted(filtered.keys()))
        for path in allPaths:
            name = os.path.splitext(os.path.basename(path))[0]
            sub = QStandardItem(name)
            sub.setData(path)
            item.appendRow(sub)

    def clear(self):
        self.__model.clear()
