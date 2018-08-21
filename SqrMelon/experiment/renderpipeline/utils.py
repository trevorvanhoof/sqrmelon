from contextlib import contextmanager

from qtutil import *


def lerp(a, b, t): return (b - a) * t + a


@contextmanager
def blankDialog(parent, title):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    main = vlayout()
    dialog.setLayout(main)
    buttonbar = hlayout()
    buttonbar.addStretch()
    ok = QPushButton('Ok')
    buttonbar.addWidget(ok)
    cancel = QPushButton('Cancel')
    buttonbar.addWidget(cancel)
    yield dialog
    main.addLayout(buttonbar)
    ok.clicked.connect(dialog.accept)
    cancel.clicked.connect(dialog.reject)
    dialog.exec_()


def tableView(table, mainLayout, name, onAdd, onDelete, onEdit):
    add = QPushButton('Add %s' % name)
    mainLayout.addWidget(add)
    add.clicked.connect(onAdd)
    delete = QPushButton('Delete selected %ss' % name)
    mainLayout.addWidget(delete)
    delete.clicked.connect(onDelete)
    table.horizontalHeader().hide()
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(22)
    table.setSelectionMode(QListView.ExtendedSelection)
    table.setModel(QStandardItemModel())
    mainLayout.addWidget(table)
    table.model().itemChanged.connect(onEdit)


def menuAction(menu, label, keySequence, callback):
    a = menu.addAction(label)
    a.setShortcut(QKeySequence(keySequence))
    a.triggered.connect(callback)
