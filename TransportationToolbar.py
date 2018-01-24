from PySide import QtGui
import FreeCADGui as Gui

last = False
mw = Gui.getMainWindow()


def onWorkbenchActivated():

    global last

    active = Gui.activeWorkbench().__class__.__name__

    tb_trans_general = mw.findChild(QtGui.QToolBar, "Transportation")
    tb_trans_align = mw.findChild(QtGui.QToolBar, "Transportation alignment")

    tb_sketcher = []
    tb_sketcher.append(mw.findChild(QtGui.QToolBar, "Sketcher"))
    tb_sketcher.append(mw.findChild(QtGui.QToolBar, "Sketcher geometries"))
    tb_sketcher.append(mw.findChild(QtGui.QToolBar, "Sketcher constraints"))

    if tb_sketcher and last and active == "SketcherWorkbench":

        tb_trans_general.hide()
        tb_trans_align.show()
        tb_trans_align.active = True
        for tb_ in tb_sketcher:
            tb_.hide()

        last = False

    elif active == "TransportationWorkbench":
        tb_trans_general.show()
        tb_trans_align.hide()
        last = True

    else:

        for tb_ in tb_sketcher:
            if tb_:
                tb_.show()

        last = False

mw.workbenchActivated.connect(onWorkbenchActivated)
