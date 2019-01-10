#!/usr/bin/env python
# -*- coding: utf-8 -*-

#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 Joel Graff <monograff76@gmail.com                  *
#*                                                                         *
#*   Adapted from Parts Library macro (PartsLibrary.FCMacro) created by    *
#*   Yorik van Havre                                                       *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************
from __future__ import print_function

__title__="FreeCAD Transportation Template Library"
__author__ = "Joel Graff"
__url__ = "http://www.freecadweb.org"

'''
FreeCAD Transportation Library
'''

import sys, FreeCAD, FreeCADGui, Part, zipfile, tempfile, Mesh, os, subprocess
from PySide import QtGui, QtCore

PARAMETER_PATH = 'User parameter:BaseApp/Preferences/Mod/Transportation'
param = FreeCAD.ParamGet(PARAMETER_PATH)
LIBRARY_PATH = param.GetString('TemplateLibPath')

#encoding error trap
_encoding = None

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
except AttributeError:
    _encoding = -1

def translate(context, text, utf8_decode = _encoding):

    #compare to ensure utf8 encoding is skipped if not available
    return QtGui.QApplication.translate(context, text, None, utf8_decode & _encoding)

class ExpFileSystemModel(QtGui.QFileSystemModel):
    '''
    a custom QFileSystemModel that displays freecad file icons
    '''

    def __init__(self):
        QtGui.QFileSystemModel.__init__(self)

    def data(self, index, role):
        if index.column() == 0 and role == QtCore.Qt.DecorationRole:

            if index.data().lower().endswith('.fcstd'):
                return QtGui.QIcon(':icons/freecad-doc.png')

            elif index.data().lower() == "private":
                return QtGui.QIcon.fromTheme("folder-lock")

        return super(ExpFileSystemModel, self).data(index, role)

class ExpDockWidget(QtGui.QDockWidget):
    '''
    a library explorer dock widget
    '''

    def __init__(self,LIBRARYPATH):
        QtGui.QDockWidget.__init__(self)

        self.lib_title = "Transportation Template Library"
        self.setObjectName("TransportationTemplateLibrary")

        # setting up a directory model that shows only fcstd
        self.dirmodel = ExpFileSystemModel()
        self.dirmodel.setRootPath(LIBRARYPATH)
        self.dirmodel.setNameFilters(["*.fcstd","*.FcStd","*.FCSTD"])
        self.dirmodel.setNameFilterDisables(0)

        self.folder = QtGui.QTreeView()
        self.folder.setModel(self.dirmodel)
        self.folder.clicked[QtCore.QModelIndex].connect(self.clicked)
        self.folder.doubleClicked[QtCore.QModelIndex].connect(self.doubleclicked)

        # Don't show columns for size, file type, and last modified
        self.folder.setHeaderHidden(True)
        self.folder.hideColumn(1)
        self.folder.hideColumn(2)
        self.folder.hideColumn(3)
        self.folder.setRootIndex(self.dirmodel.index(LIBRARYPATH))


        self.preview = QtGui.QLabel()
        self.preview.setFixedHeight(128)

        #update button
        self.updatebutton = QtGui.QPushButton()
        icon = QtGui.QIcon.fromTheme("emblem-synchronizing")
        self.updatebutton.setIcon(icon)
        self.updatebutton.clicked.connect(self.updatelibrary)
        self.updatebutton.hide()

        #config button
        self.configbutton = QtGui.QPushButton()
        icon = QtGui.QIcon.fromTheme("emblem-system")
        self.configbutton.setIcon(icon)
        self.configbutton.clicked.connect(self.setconfig)
        self.configbutton.hide()

        self.formatLabel = QtGui.QLabel()
        self.formatLabel.hide()

        #save button
        self.savebutton = QtGui.QPushButton()
        icon = QtGui.QIcon.fromTheme("document-save")
        self.savebutton.setIcon(icon)
        self.savebutton.clicked.connect(self.addtolibrary)
        self.savebutton.hide()

        #export button
        self.pushbutton = QtGui.QPushButton()
        icon = QtGui.QIcon.fromTheme("document-export")
        self.pushbutton.setIcon(icon)
        self.pushbutton.clicked.connect(self.pushlibrary)
        self.pushbutton.hide()

        #previous button
        self.prevbutton = QtGui.QPushButton()
        self.prevbutton.clicked.connect(self.showpreview)
        self.prevbutton.setStyleSheet("text-align: left;")

        #option button
        self.optbutton = QtGui.QPushButton()
        self.optbutton.clicked.connect(self.showoptions)
        self.optbutton.setStyleSheet("text-align: left;")

        #set up layout
        container = QtGui.QWidget()
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.folder, 0, 0, 1, 2)
        grid.addWidget(self.prevbutton, 1, 0, 1, 2)
        grid.addWidget(self.preview, 2, 0, 1, 2)
        grid.addWidget(self.optbutton, 3, 0, 1, 2)
        
        grid.addWidget(self.updatebutton, 4, 0, 1, 1)
        grid.addWidget(self.configbutton, 4, 1, 1, 1)
        grid.addWidget(self.formatLabel, 5, 0, 1, 2)
        grid.addWidget(self.savebutton, 9, 0, 1, 1)
        grid.addWidget(self.pushbutton, 9, 1, 1, 1)
        
        global repo
        repo = None

        try:
            import git

        except:
            FreeCAD.Console.PrintWarning("python-git not found. Git-related functions will be disabled\n")

        else:
            try:
                repo = git.Repo(LIBRARY_PATH)

            except:
                FreeCAD.Console.PrintWarning("Your library is not a valid Git repository. Git-related functions will be disabled\n")

            else:
                if not repo.remotes:
                    FreeCAD.Console.PrintWarning("No remote repository set. Git-related functions will be disabled\n")
                    repo = None

        if not repo:
            self.updatebutton.setEnabled(False)
            self.pushbutton.setEnabled(False)
            
        self.retranslateUi()
        container.setLayout(grid)
        self.setWidget(container)

    def retranslateUi(self):

        self.setWindowTitle(translate(self.lib_title, "Parts Library"))
        self.updatebutton.setText(translate(self.lib_title, "Update from Git"))
        self.configbutton.setText(translate(self.lib_title, "Config"))
        self.formatLabel.setText(translate(self.lib_title, "Add to library"))
        self.savebutton.setText(translate(self.lib_title, "Save"))
        self.pushbutton.setText(translate(self.lib_title, "Push to Git"))
        self.optbutton.setText(translate(self.lib_title, "Options"))
        self.prevbutton.setText(translate(self.lib_title, "Preview"))

    def clicked(self, index):

        path = self.dirmodel.filePath(index)

        if path.lower().endswith(".fcstd"):

            zfile = zipfile.ZipFile(path)
            files = zfile.namelist()

            # check for meta-file if it's really a FreeCAD document
            if files[0] == "Document.xml":

                image = "thumbnails/Thumbnail.png"

                if image in files:

                    image = zfile.read(image)
                    thumbfile = tempfile.mkstemp(suffix='.png')[1]
                    thumb = open(thumbfile, "wb")
                    thumb.write(image)
                    thumb.close()
                    im = QtGui.QPixmap(thumbfile)
                    self.preview.setPixmap(im)

                    return

        self.preview.clear()

    def doubleclicked(self, index):

        path = self.dirmodel.filePath(index)

        FreeCADGui.ActiveDocument.mergeProject(path)
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def addtolibrary(self):

        dialog = QtGui.QFileDialog.getSaveFileName(None, "Choose category and set filename (no extension)", LIBRARY_PATH)

        if dialog != '':

            FCfilename = dialog[0] + ".fcstd"
            FreeCAD.ActiveDocument.saveCopy(FCfilename)

    def pushlibrary(self):

        modified_files = [f for f in repo.git.diff("--name-only").split("\n") if f]
        untracked_files = [f for f in repo.git.ls_files("--other","--exclude-standard").split("\n") if f]

        import ArchServer

        d = ArchServer._ArchGitDialog()
        d.label.setText(str(len(modified_files)+len(untracked_files))+" new and modified file(s)")
        d.lineEdit.setText("Changed " + str(modified_files))
        d.checkBox.hide()
        d.radioButton.hide()
        d.radioButton_2.hide()
        r = d.exec_()

        if r:
            for o in modified_files + untracked_files:
                repo.git.add(o)
            repo.git.commit(m=d.lineEdit.text())
            if d.checkBox.isChecked():
                repo.git.push()

    def updatelibrary(self):
        repo.git.pull()

    def setconfig(self):
        d = ConfigDialog()

        if repo:
            d.lineEdit.setText(repo.remote().url)

            if hasattr(repo.remote(),"pushurl"):
                d.lineEdit_2.setText(repo.remote().pushurl)

            else:
                d.lineEdit_2.setText(repo.remote().url)

        else:
            d.groupBox.setEnabled(False)
            d.groupBox_2.setEnabled(False)

        r = d.exec_()

    def showoptions(self):

        controls = [self.updatebutton, self.configbutton, self.formatLabel, self.savebutton, self.pushbutton]
        tree = [self.preview]

        if self.updatebutton.isVisible():

            for c in controls:
                c.hide()

            for c in tree:
                c.show()

            self.optbutton.setText(QtGui.QApplication.translate(self.lib_title, "Options", None, _encoding))

        else:

            for c in controls:
                c.show()

            for c in tree:
                c.hide()

            self.optbutton.setText(QtGui.QApplication.translate(self.lib_title, "Options", None, _encoding))

    def showpreview(self):

        if self.preview.isVisible():

            self.preview.hide()
            self.prevbutton.setText(QtGui.QApplication.translate(self.lib_title, "Preview", None, _encoding))

        else:

            self.preview.show()
            self.prevbutton.setText(QtGui.QApplication.translate(self.lib_title, "Preview", None, _encoding))



class ConfigDialog(QtGui.QDialog):

    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setObjectName("GitConfig")
        self.resize(420, 250)
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        
        self.groupBox_3 = QtGui.QGroupBox(self)
        self.groupBox_3.setObjectName("groupBox_3")
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.lineEdit_3 = QtGui.QLineEdit(self.groupBox_3)
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.horizontalLayout_3.addWidget(self.lineEdit_3)
        self.pushButton_3 = QtGui.QPushButton(self.groupBox_3)
        self.pushButton_3.setObjectName("pushButton_3")
        self.horizontalLayout_3.addWidget(self.pushButton_3)
        self.verticalLayout.addWidget(self.groupBox_3)
        
        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit = QtGui.QLineEdit(self.groupBox)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.pushButton = QtGui.QPushButton(self.groupBox)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton)
        self.verticalLayout.addWidget(self.groupBox)
        
        self.groupBox_2 = QtGui.QGroupBox(self)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lineEdit_2 = QtGui.QLineEdit(self.groupBox_2)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.verticalLayout_2.addWidget(self.lineEdit_2)
        self.label = QtGui.QLabel(self.groupBox_2)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.verticalLayout.addWidget(self.groupBox_2)
        
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi()
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), self.reject)
        QtCore.QObject.connect(self.pushButton, QtCore.SIGNAL("clicked()"), self.setdefaulturl)
        QtCore.QObject.connect(self.pushButton_3, QtCore.SIGNAL("clicked()"), self.changepath)
        QtCore.QMetaObject.connectSlotsByName(self)
        
        librarypath = FreeCAD.ParamGet('User parameter:Plugins/parts_library').GetString('destination','')
        self.lineEdit_3.setText(librarypath)

    def retranslateUi(self):

        self.setWindowTitle(QtGui.QApplication.translate(self.lib_title, "Parts library configuration", None, _encoding))
        self.groupBox.setTitle(QtGui.QApplication.translate(self.lib_title, "Pull server (where you get your updates from)", None, _encoding))
        self.lineEdit.setToolTip(QtGui.QApplication.translate(self.lib_title, "Enter the URL of the pull server here", None, _encoding))
        self.pushButton.setToolTip(QtGui.QApplication.translate(self.lib_title, "Use the official FreeCAD-library repository", None, _encoding))
        self.pushButton.setText(QtGui.QApplication.translate(self.lib_title, "use official", None, _encoding))
        self.groupBox_2.setTitle(QtGui.QApplication.translate(self.lib_title, "Push server (where you push your changes to)", None, _encoding))
        self.lineEdit_2.setToolTip(QtGui.QApplication.translate(self.lib_title, "Enter the URL of the push server here", None, _encoding))
        self.label.setText(QtGui.QApplication.translate(self.lib_title, "Warning: You need write permission on this server", None, _encoding))
        self.groupBox_3.setTitle(QtGui.QApplication.translate(self.lib_title, "Library path", None, _encoding))
        self.lineEdit_3.setToolTip(QtGui.QApplication.translate(self.lib_title, "Enter the path to your parts library", None, _encoding))
        self.pushButton_3.setToolTip(QtGui.QApplication.translate(self.lib_title, "Browse to your path library", None, _encoding))
        self.pushButton_3.setText(QtGui.QApplication.translate(self.lib_title, "...", None, _encoding))

    def setdefaulturl(self):
        #self.lineEdit.setText("https://github.com/FreeCAD/FreeCAD-library.git")
        pass
        
    def changepath(self):
        librarypath = FreeCAD.ParamGet('User parameter:Plugins/parts_library').GetString('destination','')
        np = QtGui.QFileDialog.getExistingDirectory(self,"Location of your existing Parts library",librarypath)
        if np:
            self.lineEdit_3.setText(np)

    def accept(self):
        if repo:
            cw = repo.remote().config_writer
            if self.lineEdit.text():
                cw.set("url", str(self.lineEdit.text()))
            if self.lineEdit_2.text():
                cw.set("pushurl", str(self.lineEdit_2.text()))
            if hasattr(cw,"release"):
                cw.release()
        if self.lineEdit_3.text():
            FreeCAD.ParamGet(PARAMETER_PATH).SetString('TemplateLibPath',self.lineEdit_3.text())
        QtGui.QDialog.accept(self)

def show():
    '''
    Show the template library window
    '''
    if not LIBRARY_PATH:

        dialog = QtGui.QFileDialog.getExistingDirectory(None, QtGui.QApplication.translate("Transportation Template Library", "Location of library", None, _encoding))

        param.SetString('TemplateLibPath',dialog)
        LIBRARY_PATH = param.GetString('TemplateLibPath')

    if QtCore.QDir(LIBRARY_PATH).exists():
        m = FreeCADGui.getMainWindow()
        w = m.findChild(QtGui.QDockWidget,"TransportationTemplateLibrary")
        if w:
            if hasattr(w,"isVisible"):
                if w.isVisible():
                    w.hide()
                else:
                    w.show()
            else:
                # something went wrong with our widget... Recreate it
                del w
                m.addDockWidget(QtCore.Qt.RightDockWidgetArea,ExpDockWidget(LIBRARY_PATH))
        else:
            m.addDockWidget(QtCore.Qt.RightDockWidgetArea,ExpDockWidget(LIBRARY_PATH))
    else:
        print("Library path ", LIBRARY_PATH, "not found.")
