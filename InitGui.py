#************************************************************************
#*									                                    *
#*   Copyright (c) 2017							                        * 
#*   <monograff76@gmail.com>						                    * 
#*									                                    *
#*  This program is free software; you can redistribute it and/or modify*
#*  it under the terms of the GNU Lesser General Public License (LGPL)	*
#*  as published by the Free Software Foundation; either version 2 of	*
#*  the License, or (at your option) any later version.			        *
#*  for detail see the LICENCE text file.				                *
#*									                                    *
#*  This program is distributed in the hope that it will be useful,	    *
#*  but WITHOUT ANY WARRANTY; without even the implied warranty of	    *
#*  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the	    *
#*  GNU Library General Public License for more details.		        *
#*									                                    *
#*  You should have received a copy of the GNU Library General Public	*
#*  License along with this program; if not, write to the Free Software	*
#*  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#*  USA									                                *
#*									                                    *
#************************************************************************

import FreeCAD, FreeCADGui
import sys
import TransportationToolbar

class TransportationWorkbench (Workbench):

    MenuText = "Transportation Workbench"
    ToolTip = "A description of my workbench"
    Icon = '''icons/roadnrail_16.xpm'''

    def Initialize(self):

        import NewAlignment, Tangent, Curve1, Curve2, Curve3, CurveSpiral

        Gui.activateWorkbench ("SketcherWorkbench")

        self.transpolist = ["NewAlignment", "Tangent", "Curve1", "Curve2", 
                            "Curve3", "CurveSpiral", "Sketcher_NewSketch"]

        self.policieslist = ["Edit..."]

        self.appendToolbar("Transportation",self.transpolist)
        self.appendMenu("Transportation",self.transpolist)
        self.appendMenu(["Transportation","Policies"],self.policieslist)

    def Activated(self):
        "This function is executed when the workbench is activated"
        return

    def Deactivated(self):
        "This function is executed when the workbench is deactivated"
        return

    def ContextMenu(self, recipient):
        # "recipient" will be either "view" or "tree"
        self.appendContextMenu("My commands",self.list)

    def GetClassName(self): 
        # this function is mandatory if this is a full python workbench
        return "Gui::PythonWorkbench"
       
Gui.addWorkbench(TransportationWorkbench())
