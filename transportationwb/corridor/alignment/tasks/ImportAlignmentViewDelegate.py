# -*- coding: utf-8 -*-
# **************************************************************************
# *                                                                        *
# *  Copyright (c) 20XX Joel Graff <monograff76@gmail.com>                         *
# *                                                                        *
# *  This program is free software; you can redistribute it and/or modify  *
# *  it under the terms of the GNU Lesser General Public License (LGPL)    *
# *  as published by the Free Software Foundation; either version 2 of     *
# *  the License, or (at your option) any later version.                   *
# *  for detail see the LICENCE text file.                                 *
# *                                                                        *
# *  This program is distributed in the hope that it will be useful,       *
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *  GNU Library General Public License for more details.                  *
# *                                                                        *
# *  You should have received a copy of the GNU Library General Public     *
# *  License along with this program; if not, write to the Free Software   *
# *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *  USA                                                                   *
# *                                                                        *
# **************************************************************************

'''
QItemStyledDelegate class for Task QTableView
'''

from PySide import QtGui, QtCore

class ImportAlignmentViewDelegate(QtGui.QStyledItemDelegate):

    combo_box_model = ['Select...', 'Northing', 'Easting', 'Bearing', 'Distance', 'Radius', 'Degree']

    def __init__(self, parent=None):

        QtGui.QStyledItemDelegate.__init__(self, parent)
        self._is_editing = False
        self.combo_box = None

    #def initStyleOption(self, option, index):

    #    super(ImportAlignmentViewDelegate, self).initStyleOption(option, index)

    #    if index.row() > 0:
    #        option.backgroundBrush = QtGui.QColor(128, 128, 128)

    def paint(self, painter, option, index):

        painter.save()

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QColor(215, 215, 215))
        painter.drawRect(option.rect)

        if index.isValid():
            painter.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128)))
            value = index.data(QtCore.Qt.DisplayRole)
            painter.drawText(option.rect, QtCore.Qt.AlignCenter, value)

        painter.restore()

    def createEditor(self, parent, option, index):

        if index.row() > 0:
            return super(ImportAlignmentViewDelegate, self).createEditor(parent, option, index)

        self.combo_box = QtGui.QComboBox(parent)
        self.combo_box.addItems(ImportAlignmentViewDelegate.combo_box_model)

        value = index.data(QtCore.Qt.DisplayRole)

        #iterate the combo_box_model items, testing to see if they are found in the current index data
        contains_value = [a in value for a in ImportAlignmentViewDelegate.combo_box_model]

        indices = [i for i, x in enumerate(contains_value) if i]

        if indices:
            self.combo_box.setCurrentIndex(contains_value[indices[0]])

        return self.combo_box

    def setEditorData(self, editor, index):

        self._is_editing = True

        value = index.data(QtCore.Qt.EditRole) or index.data(QtCore.Qt.DisplayRole)

        if editor.metaObject().className() in ['QSpinBox', 'QDoubleSpinBox']:
            editor.setValue(value)
        else:
            editor.setText(value)

    def setModelData(self, editor, model, index):

        super(ImportAlignmentViewDelegate, self).setModelData(editor, model, index)

        self._is_editing = False

    def isEditing(self):

        return self._is_editing
