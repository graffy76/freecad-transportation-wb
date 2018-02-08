"""
Provides basic selection services for the Transportation Workbench.
These services include selection validation for specific operations (append/
insert), as well as testing for specific conditions (connected/constrained geometry)
"""

from PySide import QtGui
import FreeCADGui as Gui
import FreeCAD as App

class SelectionContainer():
    """
    A data type for storing the active selection by the types of objects selected.
    """

    def __init__(self):
        self.vertices = []
        self.lines = []
        self.curves = []

def _find_geometry(sketch_object, shape):

    vtx_count = len(shape.Vertexes)

    #iterate each geometry element, comparing against the passed shape
    for geom in sketch_object.Geometry:

        geom_verts = geom.toShape().Vertexes

        #skip if vertex counts don't match
        if len(geom_verts) != vtx_count:
            continue

        found = True

        #iterate each vertex, comparing coordinates
        for i in range(0, vtx_count-1):

            found = found & \
                (geom_verts[i].X == shape.Vertexes[i].X) & \
                (geom_verts[i].Y == shape.Vertexes[i].Y)

            if not found:
                break

        #return the geometry if it matches the passed shape
        if found:
            return geom

    return None

def is_construction(sketch_object, shape):

    geom = _find_geometry(sketch_object, shape)

    if geom is None:
        return False

    return geom.Construction


def is_insert_selection():
    """
    Returns true if two adjacent objects are selected.
    """

    selection = Gui.Selection.getSelectionEx()

    if len(selection) != 2:
        return False

    object_one = selection[0].SubObjects[0]
    object_two = selection[1].SubObjects[0]

    return is_connected(object_one, object_two)

def is_connected(object_one, object_two):
    """
    Returns true for objects which share at least one common Vertex.
    """

    for vert_one in object_one.Vertexes:
        for vert_two in object_two.Vertexes:
            if (vert_one.X == vert_two.X) and (vert_one.y == vert_two.y):
                return True

    return False

def is_append_selection():
    """
    Returns true if the last object (or no object) is selected.
    """

    selection = Gui.Selection.getSelectionEx()

    if len(selection) > 1:
        return False

    last_object_verts = \
        App.ActiveDocument.ActiveObject.Geometry[0].toShape().Vertexes

    selected_object_verts = selection[0].SubObjects[0].Vertexes

    if (selected_object_verts[0] == last_object_verts[0]) and \
        (selected_object_verts[1] == last_object_verts[1]):
        return True

    return False

def notify_selection_error(title):
    """
    Notifies user in case of selection error.
    Title of error is passed as an argument.
    """

    QtGui.QMessageBox.critical(
        None, title, "Select two adjacent elements to insert between.")


def get_selection():
    """
    Returns a SelectionContainer object which categorizes
    the selected objects by type: Line, Curve, and Vertex.
    """

    selected = Gui.Selection.getSelectionEx()[0].SubObjects
    sel_len = len(selected)
    result = SelectionContainer()

    for _x in range(0, sel_len):

        shape_type = selected[_x].ShapeType

        if shape_type == 'Vertex':
            result.vertices.append(selected[_x])

        elif shape_type == 'Edge':

            if 'Line' in str(selected[_x].Curve):
                result.lines.append(selected[_x])
            else:
                result.curves.append(selected[_x])
