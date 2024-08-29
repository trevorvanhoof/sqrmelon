from __future__ import annotations

from typing import Any, Iterable, Optional, Union
from xml.etree import cElementTree

import icons
from animationgraph.curvedata import Curve, Key
from fileutil import FilePath
from projutil import currentProjectFilePath, currentScenesDirectory, currentTemplatesDirectory, iterSceneNames, SCENE_EXT
from qt import *
from qtutil import DoubleSpinBox, hlayout, vlayout
from scene import Scene
from textures import TextureManager
from util import randomColor
from xmlutil import parseXMLWithIncludes, toPrettyXml


def readChannelTemplates() -> dict[str, dict[str, Curve]]:
    templatesDir = currentTemplatesDirectory()
    channelTemplates = templatesDir.join('uniforms.xml')
    result = {}

    # legacy fallback
    if not channelTemplates.exists():
        curves = {'uOrigin.x': Curve(),
                  'uOrigin.y': Curve(),
                  'uOrigin.z': Curve(),
                  'uAngles.x': Curve(),
                  'uAngles.y': Curve(),
                  'uAngles.z': Curve()}
        result['default'] = curves
        return result

    xRoot = parseXMLWithIncludes(channelTemplates)
    for xTemplate in xRoot:
        name = xTemplate.attrib['name']
        curves = {}
        result[name] = curves
        for xChannel in xTemplate:
            curve = Curve()
            curves[xChannel.attrib['name']] = curve
            Key(0.0, float(xChannel.attrib['value']), curve).reInsert()

    return result


class Shot:
    def __init__(self, name: str, sceneName: str, start: float = 0.0, end: float = 1.0,
                 curves: Optional[dict[str, Curve]] = None,
                 textures: Optional[dict[str, FilePath]] = None,
                 speed: float = 1.0, preroll: float = 0.0) -> None:
        self.items = [QStandardItem(name),
                      QStandardItem(sceneName),
                      QStandardItem(str(start)),
                      QStandardItem(str(end)),
                      QStandardItem(str(end - start)),
                      QStandardItem(str(speed)),
                      QStandardItem(str(preroll))]
        self.curves = curves or {}
        self.textures = textures or {}
        self.color = QColor.fromRgb(*randomColor())
        self.items[0].setData(self, Qt.ItemDataRole.UserRole + 1)
        self._enabled = True
        self._pinned = False
        self.items[0].setIcon(icons.get('Checked Checkbox-48'))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self.pinned = False
        if not value:
            self.items[0].setIcon(icons.get('Unchecked Checkbox-48'))
        else:
            self.items[0].setIcon(icons.get('Checked Checkbox-48'))

    @property
    def pinned(self) -> bool:
        return self._pinned

    @pinned.setter
    def pinned(self, value: bool) -> None:
        if value:
            self.enabled = True
        self._pinned = value
        if value:
            self.items[0].setIcon(icons.get('Pin-48'))
        else:
            if not self._enabled:
                self.items[0].setIcon(icons.get('Unchecked Checkbox-48'))
            else:
                self.items[0].setIcon(icons.get('Checked Checkbox-48'))

    def evaluate(self, time: float) -> dict[str, Union[float, list[float]]]:
        time -= self.start
        time *= self.speed
        time -= self.preroll
        data: dict[str, Union[float, dict[str, float], list[float]]] = {}
        # Gather values as either single channel floats or named multi channel dicts
        for name in self.curves:
            value = self.curves[name].evaluate(time)
            if '.' in name:
                name, channel = name.split('.', 1)
                v = data.setdefault(name, {})
                assert isinstance(v, dict)
                v[channel] = value
            else:
                assert name not in data
                data[name] = value
        # Convert dict values to list values
        for name in data:
            v = data[name]
            if isinstance(v, dict):
                if 'w' in v:
                    assert set(v.keys()) == set('xyzw')
                    data[name] = [v['x'], v['y'], v['z'], v['w']]
                elif 'z' in v:
                    assert set(v.keys()) == set('xyz')
                    data[name] = [v['x'], v['y'], v['z']]
                elif 'y' in v:
                    assert set(v.keys()) == set('xy')
                    data[name] = [v['x'], v['y']]
                else:
                    assert set(v.keys()) == set('x')
                    data[name] = [v['x']]
        return data  # type: ignore

    def bake(self) -> None:
        speed = self.speed
        start = self.start
        end = self.end
        for name in self.curves:
            # offset our keys by our preroll time
            self.curves[name].move(self.preroll)
            # scale curves so we can set our speed to 1
            self.curves[name].scale(speed)
            # delete keys outside time range
            self.curves[name].trim(start, end)
        self.speed = 1.0
        self.preroll = 0.0

    def clone(self) -> Shot:
        curves: dict[str, Curve] = {}
        for name in self.curves:
            curves[name] = self.curves[name].clone()
        textures: dict[str, FilePath] = {}
        for name in self.textures:
            textures[name] = self.textures[name]
        return Shot(self.name, self.sceneName, self.start, self.end, curves, textures, self.speed, self.preroll)

    @property
    def name(self) -> str:
        return self.items[0].text()

    @property
    def sceneName(self) -> str:
        return self.items[1].text()

    @property
    def start(self) -> float:
        return float(self.items[2].text())

    @start.setter
    def start(self, value: float) -> None:
        strVal = str(value)
        if strVal == self.items[2].text():
            return
        self.items[2].setText(strVal)
        self.end = value + self.duration

    @property
    def end(self) -> float:
        return float(self.items[3].text())

    @end.setter
    def end(self, value: float) -> None:
        strVal = str(value)
        if strVal == self.items[3].text():
            return
        self.items[3].setText(strVal)
        self.duration = value - self.start

    @property
    def duration(self) -> float:
        return float(self.items[4].text())

    @duration.setter
    def duration(self, value: float) -> None:
        strVal = str(value)
        if strVal == self.items[4].text():
            return
        self.items[4].setText(strVal)
        self.end = value + self.start

    @property
    def speed(self) -> float:
        return float(self.items[5].text())

    @speed.setter
    def speed(self, value: float) -> None:
        strVal = str(value)
        if strVal == self.items[5].text():
            return
        self.items[5].setText(strVal)

    @property
    def preroll(self) -> float:
        return float(self.items[6].text())

    @preroll.setter
    def preroll(self, value: float) -> None:
        strVal = str(value)
        if strVal == self.items[6].text():
            return
        self.items[6].setText(strVal)


class FloatItemDelegate(QItemDelegate):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__editor = DoubleSpinBox()

    def setEditorData(self, editorWidget: DoubleSpinBox, index: QModelIndex) -> None:  # type: ignore
        editorWidget.setValue(float(index.data()))

    def setModelData(self, editorWidget: DoubleSpinBox, model: QAbstractItemModel, index: QModelIndex) -> None:  # type: ignore
        model.setData(index, str(editorWidget.value()))

    def createEditor(self, parentWidget: QWidget, styleOption: QStyleOption, index: QModelIndex) -> DoubleSpinBox:  # type: ignore
        self.__editor.setParent(parentWidget)
        self.__editor.editingFinished.connect(self.__commitAndCloseEditor)
        return self.__editor

    def __commitAndCloseEditor(self) -> None:
        self.commitData.emit(self.__editor)
        self.closeEditor.emit(self.__editor, QAbstractItemDelegate.EndEditHint.NoHint)


def deserializeSceneShots(sceneName: str) -> Iterable[Shot]:
    sceneFile = currentScenesDirectory().join(FilePath(sceneName).ensureExt(SCENE_EXT))
    xScene = parseXMLWithIncludes(sceneFile)

    for xShot in xScene:
        name = xShot.attrib['name']
        start = float(xShot.attrib['start'])
        end = float(xShot.attrib['end'])
        speed = float(xShot.attrib.get('speed', 1.0))  # using get for legacy file support
        preroll = float(xShot.attrib.get('preroll', 0.0))

        curves = {}
        textures: dict[str, FilePath] = {}
        for xEntry in xShot:
            if xEntry.tag.lower() == 'channel':
                curveName = xEntry.attrib['name']
                keys: list[str] = []
                if xEntry.text:
                    keys = xEntry.text.split(',')
                curve = Curve()
                for i in range(0, len(keys), 8):
                    args: tuple[float, float, float, float, float, float] = tuple(float(x) for x in keys[i:i + 6])  # type: ignore
                    curve.addKeyWithTangents(*args, tangentBroken=bool(int(keys[i + 6])), tangentMode=int(keys[i + 7]))
                curves[curveName] = curve

            if xEntry.tag.lower() == 'texture':
                textures[xEntry.attrib['name']] = FilePath(xEntry.attrib['path'])

        shot = Shot(name, sceneName, start, end, curves, textures, speed, preroll)
        if 'enabled' in xShot.attrib:
            shot.enabled = xShot.attrib['enabled'] == str(True)
        yield shot


def _saveSceneShots(sceneName: FilePath, shots: Iterable[Shot]) -> None:
    projectPath = currentProjectFilePath()
    assert projectPath is not None

    sceneFile = currentScenesDirectory().join(sceneName.ensureExt(SCENE_EXT))
    xScene = parseXMLWithIncludes(sceneFile)

    # save user camera position per scene
    userFile = projectPath.ensureExt('user')
    if userFile.exists():
        xUser = parseXMLWithIncludes(userFile)
    else:
        xUser = cElementTree.Element('user')
    if sceneFile in Scene.cache:
        cameraData = Scene.cache[sceneFile].cameraData()
        if cameraData:
            for xSub in xUser:
                if xSub.tag == 'scene' and xSub.attrib['name'] == sceneName:
                    xSub.attrib['camera'] = ','.join([str(x) for x in cameraData])  # type: ignore
                    break
            else:
                cElementTree.SubElement(xUser, 'scene', {'name': sceneName, 'camera': ','.join([str(x) for x in cameraData])})  # type: ignore

    with userFile.edit() as fh:
        fh.write(toPrettyXml(xUser))

    # remove old shots
    r = []
    for xShot in xScene:
        r.append(xShot)
    for s in r:
        xScene.remove(s)

    targets = []
    for shot in shots:
        if shot.sceneName == sceneName:
            targets.append(shot)

    for shot in targets:
        xShot = cElementTree.SubElement(xScene, 'Shot', {
            'name': shot.name,
            'scene': sceneName,
            'start': str(shot.start),
            'end': str(shot.end),
            'enabled': str(shot.enabled),
            'speed': str(shot.speed),
            'preroll': str(shot.preroll)})
        for curveName in shot.curves:
            xChannel = cElementTree.SubElement(xShot, 'Channel', {'name': curveName, 'mode': 'hermite'})
            data = []
            for key in shot.curves[curveName]:  # type: ignore
                data.append(str(key.inTangent().x))
                data.append(str(key.inTangent().y))
                data.append(str(key.point().x))
                data.append(str(key.point().y))
                data.append(str(key.outTangent().x))
                data.append(str(key.outTangent().y))
                data.append(str(int(key.tangentBroken)))
                data.append(str(key.tangentMode))
            xChannel.text = ','.join(data)
        for texName in shot.textures:
            cElementTree.SubElement(xShot, 'Texture', {'name': texName, 'path': shot.textures[texName]})

    with sceneFile.edit() as fh:
        fh.write(toPrettyXml(xScene))


class ShotView(QTableView):
    viewShotAction = Signal(float, float, object)
    pinShotAction = Signal(Shot)
    shotsEnabled = Signal(list)
    shotsDisabled = Signal(list)
    findSceneRequest = Signal(str)

    def __init__(self) -> None:
        super(ShotView, self).__init__()
        self.__menu = QMenu()
        self.__menu.addAction(icons.get('Visible-48'), 'View').triggered.connect(self.__onViewShot)
        self.__menu.addAction(icons.get('Pin-48'), 'Pin').triggered.connect(self.onPinShot)
        self.__menu.addAction(icons.get('Checked Checkbox-48'), 'Enable').triggered.connect(self.__onEnableShot)
        self.__menu.addAction(icons.get('Unchecked Checkbox-48'), 'Disable').triggered.connect(self.__onDisableShot)
        self.__menu.addAction(icons.get('Link-48'), 'Select scene').triggered.connect(self.__onSelectScene)
        self.__menu.addAction(icons.get('Picture-48'), 'Edit textures').triggered.connect(self.__onManageTextures)
        self.__menu.addAction(icons.get('Bake'), 'Bake preroll && speed').triggered.connect(self.__onBakeShot)
        self.__row = -1

    def model(self) -> ShotModel:
        return super().model()  # type: ignore

    def __onBakeShot(self) -> None:
        item = self.model().item(self.__row)
        item.text()
        item.data(Qt.ItemDataRole.UserRole + 1).bake()

    def __onManageTextures(self) -> None:
        item = self.model().item(self.__row)
        TextureManager(item.data(Qt.ItemDataRole.UserRole + 1)).exec_()

    def __onSelectScene(self) -> None:
        self.findSceneRequest.emit(str(self.model().item(self.__row, 1).text()))

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.__row = self.rowAt(event.y())
        if self.__row != -1:
            self.__menu.popup(self.mapToGlobal(event.pos()))

    def __onViewShot(self) -> None:
        self.viewShotAction.emit(float(self.model().item(self.__row, 2).text()),
                                 float(self.model().item(self.__row, 3).text()),
                                 self.model().item(self.__row).data(Qt.ItemDataRole.UserRole + 1))

    def onPinShot(self, row: Optional[int] = None) -> None:
        item = self.model().item(self.__row if row is None else row)
        if not item:
            return
        self.shotsEnabled.emit([item.data(Qt.ItemDataRole.UserRole + 1)])
        self.pinShotAction.emit(item.data(Qt.ItemDataRole.UserRole + 1))

    def __onEnableShot(self) -> None:
        shots = []
        for index in self.selectionModel().selectedRows():
            item = self.model().item(index.row(), 0)
            shot = item.data(Qt.ItemDataRole.UserRole + 1)
            shots.append(shot)
            shot.enabled = True
        self.shotsEnabled.emit(shots)

    def __onDisableShot(self) -> None:
        shots = []
        for index in self.selectionModel().selectedRows():
            item = self.model().item(index.row(), 0)
            shot = item.data(Qt.ItemDataRole.UserRole + 1)
            shots.append(shot)
            shot.enabled = False
            shot.pinned = False
        self.shotsDisabled.emit(shots)


class ShotModel(QSortFilterProxyModel):
    # noinspection PyMethodOverriding
    def lessThan(self, lhs: Union[QModelIndex, QPersistentModelIndex], rhs: Union[QModelIndex, QPersistentModelIndex]) -> bool:
        lv = lhs.data()
        rv = rhs.data()
        try:
            return float(lv) < float(rv)
        except (ValueError, TypeError):
            return lv < rv

    def setSourceModel(self, sourceModel: ShotItemModel) -> None:  # type: ignore
        super().setSourceModel(sourceModel)

    def sourceModel(self) -> ShotItemModel:
        return super().sourceModel()  # type: ignore

    def item(self, row: int, col: int = 0) -> QStandardItem:
        return self.sourceModel().itemFromIndex(self.mapToSource(self.index(row, col)))


class ShotItemModel(QStandardItemModel):
    # noinspection PyMethodOverriding
    def flags(self, modelIndex: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        flags = super(ShotItemModel, self).flags(modelIndex)
        if modelIndex.column() == 1:
            return flags & ~Qt.ItemFlag.ItemIsEditable
        return flags


class ShotManager(QWidget):
    currentChanged = Signal(Shot)
    shotPinned = Signal(Shot)

    def __init__(self) -> None:
        super(ShotManager, self).__init__()
        mainLayout = vlayout()
        self.setLayout(mainLayout)
        beltLayout = hlayout()
        btn = QPushButton(icons.get('Film Reel Create-48'), '')
        btn.setToolTip('Create shot-48')
        btn.setStatusTip('Create shot-48')
        btn.clicked.connect(self.createShot)
        beltLayout.addWidget(btn)
        btn = QPushButton(icons.get('Film Reel Copy-48'), '')
        btn.setToolTip('Duplicate shot-48')
        btn.setStatusTip('Duplicate shot-48')
        btn.clicked.connect(self.__duplicateSelectedShots)
        beltLayout.addWidget(btn)
        # btn = QPushButton(icons.get('Film Reel Merge-48'), '') # what do we do when selected shots are not adjacent?
        # btn.setToolTip('Merge shots')
        # beltLayout.addWidget(btn)
        # btn = QPushButton(icons.get('Film Reel Cut-48'), '')
        # btn.setToolTip('Cut shots')
        # beltLayout.addWidget(btn)
        btn = QPushButton(icons.get('Film Reel Delete-48'), '')
        btn.setToolTip('Delete shots-48')
        btn.setStatusTip('Delete shots-48')
        btn.clicked.connect(self.__deleteSelectedShots)
        beltLayout.addWidget(btn)
        mainLayout.addLayout(beltLayout)
        self.__table = ShotView()
        self.findSceneRequest = self.__table.findSceneRequest
        self.viewShotAction = self.__table.viewShotAction
        self.__table.pinShotAction.connect(self.onPinShot)
        self.shotsEnabled = self.__table.shotsEnabled
        self.shotsDisabled = self.__table.shotsDisabled
        delegate = FloatItemDelegate()
        self.__table.setItemDelegateForColumn(2, delegate)
        self.__table.setItemDelegateForColumn(3, delegate)
        mainLayout.addWidget(self.__table)
        self.__model = ShotItemModel()
        shots = ShotModel()
        shots.setSourceModel(self.__model)
        self.__model.setColumnCount(7)
        self.__model.setHorizontalHeaderLabels(['Name', 'Scene', 'Start', 'End', 'Duration', 'Speed', 'Preroll'])
        self.__table.setModel(shots)
        self.__table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.__table.setSortingEnabled(True)
        self.__table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        self.__table.selectionModel().currentChanged.connect(self.__onCurrentChanged)
        self.__loadAllShots()
        # Duration changes end, start changes end, end changes duration.
        self.shotChanged.connect(self.__onPropagateShotChange)

    def shotView(self) -> ShotView:
        return self.__table

    def __onPropagateShotChange(self, changedItem: QStandardItem) -> None:
        col = changedItem.column()
        if col in (2, 3, 4):
            shot = self.__model.item(changedItem.row()).data()
            value = float(changedItem.text())
            if col == 2:
                shot.end = value + shot.duration
            elif col == 3:
                shot.duration = value - shot.start
            elif col == 4:
                shot.end = shot.start + value

    def onPinShot(self, pinShot: Shot) -> None:
        for shot in self.shots():
            shot.pinned = shot == pinShot
        self.shotPinned.emit(pinShot)

    @property
    def shotChanged(self) -> SignalInstance:
        return self.__model.itemChanged  # type: ignore

    def shotAtTime(self, time: float) -> Optional[Shot]:
        candidate: Optional[Shot] = None
        for row in range(self.__model.rowCount()):
            shot = self.__model.item(row).data(Qt.ItemDataRole.UserRole + 1)
            if not shot.enabled:
                continue
            if shot.pinned:
                return shot
            if shot.start <= time < shot.end:
                candidate = shot
        return candidate

    def additionalTextures(self, time: float) -> dict[str, FilePath]:
        shot = self.shotAtTime(time)
        if not shot:
            return {}
        return shot.textures

    def evaluate(self, time: float) -> dict[str, Union[float, list[float]]]:
        shot = self.shotAtTime(time)
        if not shot:
            return {}
        return shot.evaluate(time)

    def projectOpened(self) -> None:
        self.__loadAllShots()

    def __loadAllShots(self) -> None:
        if currentProjectFilePath() is None:
            self.setEnabled(False)
            return
        self.setEnabled(True)
        self.__model.clear()
        # model.clear() removes the header labels
        self.__model.setHorizontalHeaderLabels(['Name', 'Scene', 'Start', 'End', 'Duration', 'Speed', 'Preroll'])
        for sceneName in iterSceneNames():
            for shot in deserializeSceneShots(sceneName):
                self.__model.appendRow(shot.items)

        self.__table.sortByColumn(2, Qt.SortOrder.AscendingOrder)

    def shots(self) -> Iterable[Shot]:
        for row in range(self.__model.rowCount()):
            shot = self.__model.item(row).data(Qt.ItemDataRole.UserRole + 1)
            yield shot

    def selectShot(self, shot: Shot) -> None:
        idx = self.__table.model().mapFromSource(shot.items[0].index())
        self.__table.clearSelection()
        self.__table.selectRow(idx.row())

    def saveAllShots(self) -> None:
        for sceneName in iterSceneNames():
            _saveSceneShots(sceneName, self.shots())

    def __onCurrentChanged(self, current: QModelIndex, _: Any) -> None:
        row = self.__table.model().mapToSource(current).row()
        self.currentChanged.emit(self.__model.item(row).data(Qt.ItemDataRole.UserRole + 1))

    def __selectedShots(self) -> Iterable[Shot]:
        rows = []
        for idx in self.__table.selectedIndexes():
            row = self.__table.model().mapToSource(idx).row()
            rows.append(row)
        for row in set(rows):
            yield self.__model.item(row).data(Qt.ItemDataRole.UserRole + 1)

    def __shotNames(self) -> Iterable[str]:
        for shot in self.shots():
            yield shot.name

    def createShot(self, initialSceneName: Optional[FilePath] = None) -> None:
        sceneNames = list(iterSceneNames())
        if not sceneNames:
            QMessageBox.warning(self, 'Can\'t create shot!', 'Can not create shots before creating at least 1 scene.')
            return

        diag = QDialog(self)
        layout = vlayout()
        diag.setLayout(layout)
        diag.setWindowTitle('Create shot')

        layout.addWidget(QLabel('Name:'))
        name = QLineEdit(initialSceneName or '')
        layout.addWidget(name)

        layout.addWidget(QLabel('Scene:'))
        scenes = QComboBox()
        scenes.addItems(sceneNames)
        scenes.setEditable(False)
        layout.addWidget(scenes)

        channelTemplates = readChannelTemplates()
        channelTemplateNames = list(channelTemplates.keys())
        templateIndex = 0
        if 'default' in channelTemplateNames:
            channelTemplateNames.index('default')

        channelTemplateSelector = None
        if len(channelTemplateNames) > 1:
            layout.addWidget(QLabel('Channels:'))
            channelTemplateSelector = QComboBox()
            channelTemplateSelector.addItems(channelTemplateNames)
            channelTemplateSelector.setEditable(False)
            layout.addWidget(scenes)

        create = QPushButton('Create')
        create.clicked.connect(diag.accept)
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(diag.reject)

        buttonBar = hlayout()
        buttonBar.addStretch(1)
        buttonBar.addWidget(create)
        buttonBar.addWidget(cancel)
        layout.addLayout(buttonBar)

        if initialSceneName and str(initialSceneName) in sceneNames:
            scenes.setCurrentIndex(sceneNames.index(initialSceneName))
            # if there is a channel template for this scene, default to it
            if initialSceneName in channelTemplateNames:
                templateIndex = channelTemplateNames.index(initialSceneName)
        else:
            scenes.setCurrentIndex(0)

        if channelTemplateSelector is not None:
            channelTemplateSelector.setCurrentIndex(templateIndex)

        diag.exec_()

        if diag.result() != QDialog.DialogCode.Accepted:
            return
        if not name.text():
            QMessageBox.warning(self, 'Could not create shot', 'Please enter a name.')
            return

        start = 0.0
        selected = list(self.__selectedShots())
        if selected:
            start = selected[-1].start

        if channelTemplateSelector is not None:
            channelTemplateName = channelTemplateSelector.currentText()
            curves = channelTemplates[channelTemplateName]
        else:
            curves = list(channelTemplates.values())[0]

        shot = Shot(name.text(), scenes.currentText(), start, start + 8.0, curves)
        self.__model.appendRow(shot.items)

    def __duplicateSelectedShots(self) -> None:
        for shot in self.__selectedShots():
            clone = shot.clone()
            self.__model.appendRow(clone.items)

    def __deleteShots(self, rows: list[int]) -> None:
        rows = list(set(rows))
        rows.sort(key=lambda x: -x)
        for row in rows:
            self.__model.removeRow(row)

    def __deleteSelectedShots(self) -> None:
        rows = []
        for idx in self.__table.selectedIndexes():
            row = self.__table.model().mapToSource(idx).row()
            rows.append(row)
        self.__deleteShots(rows)

    def onDeleteScene(self, sceneName: str) -> None:
        rows = []
        for row in range(self.__model.rowCount()):
            if sceneName == str(self.__model.item(row, 1).text()):
                rows.append(row)
        self.__deleteShots(rows)
