"""
Creates tanget alignment geometry for the Transportation wb
"""

import FreeCAD as App
import FreeCADGui as Gui
import GeometrySelection

class Tangent():

    def __init__(self):
        #self.activeObject = App.ActiveDocument.ActiveObject
        pass

    def GetResources(self):
        """
        Icon resources.
        """
        return {'Pixmap'  : 'My_Command_Icon',
                'Accel' : "Shift+T",
                'MenuText': "Tangent",
                'ToolTip' : "Add a tangnet"}

    def Activated(self):
        """
        Executes the tangent construction.
        """
        print GeometrySelection.is_insert_selection()

        sketch_object = App.ActiveDocument.Horizontal_Geometry
        shape = Gui.Selection.getSelectionEx()[0].SubObjects[0]

        print GeometrySelection.is_construction(sketch_object, shape)
        #validate the selection, returning if invalid
        #selected_geometry = self._getSelection()

        #int count = len(selected_geometry)

        #create the new geometry
        #newGeometry = Part.LineSegment (
         #   FreeCAD.Vector (0.0, 0.0), FreeCAD.Vector (1.0, 1.0))

        #insert the geometry
        #unless it's true north, then add a angle constraint

        return

    def IsActive(self):
        """
        Returns true if there is an active document
        """
        return True

Gui.addCommand('Tangent', Tangent())
