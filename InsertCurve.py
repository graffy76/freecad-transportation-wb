"""
Generic simple curve generator.  Will generate a curve given no
initial input, a pair of back tangents, a curve and adjacent back tangent,
and a pair of curves.  New curve is generated between selected geometries.
"""
from PySide import QtGui
import FreeCAD as App
import FreeCADGui as Gui
import GeometryUtilities as GeoUtils
import GeometryObjects as GeoObj
import CurveUtilities as CurveUtils
import os
import math
import Part
import Sketcher
import SketchElement as skel

class InsertCurve():

    def GetResources(self):

        icon_path = os.path.dirname(os.path.abspath(__file__))

        icon_path += "/icons/one_center_curve.svg"

        return {'Pixmap'  : icon_path,
                'Accel' : "Shift+0",
                'MenuText': "Simple Curve",
                'ToolTip' : "Add / Insert a simple curve",
                'CmdType' : "For Edit"}

    def IsActive(self):
        """
        Returns class active status
        """
        return Gui.ActiveDocument != None

    def Activated(self):
        """
        Generates an arc based on the selected geometry and returns
        a list containing the arc and it's corresponding back tangents
        """

        if Gui.Selection.getSelection() == []:
            self._notify_error("Selection")
            return

        self.sketch = Gui.Selection.getSelection()[0]

        #validate the selected geometry
        selection = self._validate_selection()

        if selection is None:
            return

        #if one of the geometries is a curve, need to get the opposite
        #back tangent before continuing
        geo_dict = self._get_tangents(selection)

        vertex_index = -1

        #create a new back tangent and adjust the existing arc
        #so we can place a new arc
        if geo_dict["arc"] != None:

            if geo_dict["end_tangent"] == None:
                return

            geo_dict["constraint"] = geo_dict["arc"].get_binding_constraint\
                (geo_dict["start_tangent"].index)

            #determine the index of the constrained point
            vertex_index = self._get_constrained_vertex(geo_dict["constraint"])

            if vertex_index < 0:
                self._notify_error("Invalid Constraint")
                return

            #delete the existing constraints and return any geometry
            #adjacent to the arc
            geo_dict = self._delete_constraints(geo_dict, vertex_index)

            #adjust the existing arc
            geo_dict = self._adjust_curve(geo_dict, vertex_index, 0.25)

            #create the arc back tangent
            geo_dict["new_tangent"] = \
                self._generate_new_back_tangent(geo_dict, vertex_index)

            #update the dictionary before adding the arc
            geo_dict["end_tangent"] = geo_dict["new_tangent"]

            #arc_params = self._get_arc_parameters(geo_dict)

        arc_parameters = self._get_arc_parameters(geo_dict, vertex_index)

        #create a new arc based on the specified back tangents
        new_arc = CurveUtils.create_arc(arc_parameters)

        self.sketch.addGeometry(new_arc)
        App.ActiveDocument.recompute()

        geo_dict["new arc"] = new_arc

        self._reconstrain(geo_dict, vertex_index)

        return

    def _get_arc_parameters(self, geo_dict, vertex_index):
        """
        Get the basic parameters required to define an arc

        Arguments:
        geo_dict - Dictionary of geometry
        vertex_index - Index of the arc vertex that was moved

        Returns:

        Dictionary of arc parameters with the following keys:

        location - The center of the arc as an App.Vector
        radius - The radius of the arc as a float
        start_angle - The starting angle of the arc in radians
        sweep_angle - The angle through which the arc rotates (CCW) in radians
        """

        arc = geo_dict["arc"]
        arc_vertex = arc.get_points()[vertex_index]

        arc_loc = arc.get_element().Location

        print ("arc vertex: " + str(arc_vertex))

        tangents = self._get_line_segments(geo_dict, arc_vertex)

        orthos = []
        result = {}

        #get the orthogonal for the tangent from the existing arc
        orthos.append(tangents[0].get_orthogonal(arc_vertex))

        #get the orthogonal for the opposing tangent
        tangent_vertex = tangents[1].start_point
        
        if GeoUtils.compare_vectors(geo_dict["p_i"], tangent_vertex):
            tangent_vertex = tangents[1].end_point

        orthos.append(tangents[1].get_orthogonal(tangent_vertex))

        #calculate the arc radius
        arc_rad = arc_loc.sub(tangent_vertex).Length

        #swap orthogonals to ensure counter-clockwise ordering
        cp =  orthos[0].to_vector()\
            .cross(orthos[1].to_vector())

        if cp.z < 0.0:
            orthos[0], orthos[1] = orthos[1], orthos[0]

        #set the initial offset by determining the quadrant
        quad = abs(GeoUtils.get_quadrant(arc_loc, orthos[0].start_point))

        #calculate the start angle
        start_angle = (quad - 1) * (math.pi / 2.0)

        #test for undefined slope
        if orthos[0].slope is None:
            if arc.Location.y > orthos[0].start_point.y:
                start_angle *= -1.0
        else:
            start_angle += math.atan(abs(1.0 / orthos[0].slope))

        sweep_angle = orthos[1].to_vector()\
            .getAngle(orthos[0].to_vector()) + start_angle

        return {"location": arc_loc,
                "radius": arc_rad,
                "start_angle": start_angle,
                "sweep_angle": sweep_angle}

    def _sort_vectors(self, vectors):
        """
        Takes a list of two App.Vectors and orders them
        such that the first is rotated counterclockwise from the second.
        """

        vec0 = vectors[0]
        vec1 = vectors[1]

        cross_product = vec0.cross(vectors[1])

        result = [vec0, vec1]

        if cross_product.z > 0.0:

            result = [vec1, vec0]

        return result

    def _get_line_segments(self, geo_dict, arc_vertex):
        """
        Returns two Line2d objects representing the line segments
        of the tangents to which the arc will be bound.

        Arguments:
        geo_dict - dictionary of SketchElement geometry
        arc_vertex - App.Vector of the vertex that was moved

        Returns:
        List of Line2d objects representing the exact tangents
        If tangents have a coincident endpoint, the start and end
        tangents are returned as Line2d objects.

        If one tangnet intersects another, returns the tangent segments
        from the PI to the arc's vertex and from the PI to the tangent
        endpoint which bounds the new arc's ending radius point
        """

        tangents = [\
            geo_dict["start_tangent"],\
            geo_dict["end_tangent"]\
        ]

        #return if tangents have coincident endpoints
        if (tangents[0].is_coincident(tangents[1].index)):
            return [tangents[0].as_line2d(), tangents[1].as_line2d()]

        #an arc should be a selected element
        if not geo_dict.has_key("arc"):
            self._notify_error ("No Arc")
            return None

        #get the point of intersection
        p_i = tangents[0].intersect2d(tangents[1])

        geo_dict["p_i"] = p_i

        #get the tangent segment between the arc vertex and p.i.
        arc = geo_dict["arc"].get_element()
        arc_line = GeoObj.Line2d(p_i, arc_vertex)

        #get the tangent that's split by the p_i
        split_tangent = tangents[0]

        for point in split_tangent.get_points():
            if GeoUtils.compare_vectors(p_i, point):
                split_tangent = tangents[1]

        ortho = split_tangent.as_line2d().\
            get_orthogonal(arc.Location)

        tangent_vertex = ortho.intersect(split_tangent.as_line2d())

        split_line = GeoObj.Line2d(p_i, tangent_vertex)

        #return the two tangents as 2D lines
        return [arc_line, split_line]

    def _delete_constraints(self, geo_dict, vertex_index):
        """
        Deletes existing constraints from an existing arc's end point
        and returns adjacent geometry that shares an endpoint with the
        constrained vertex
        
        Arguments:
        vertex_index - curve index constrained to the selected tangent
        geo_dict - The dictionary of selected geometry as SketchElements
        factor - The adjustment factor

        Returns:
        geo-dict with additional "adjacent" member, identifying adjacent
        geometry attached to the constrained endpoint, if any.
        """
#############
        #need to determine which constraints are bound to the point
        #if additional constraints from other geometry are applied, then
        #they need to be deleted as well and that geometry needs to be 
        #reconstrained

        #cases:
        #1.  Arc endpoints bound.  If another arc endpoint is bound to
        #this endpoint, it should be a tangent constraint.  The current
        #point, if it has two tangent constraints, one should be to the
        #tangent line, the other to the arc end point.  Delete both
        #reconstrain the other arc endpoint to the tangent line and
        #recompute.  If only one tangent constraint, should be to the
        #other arc.  If only one, and bound to tangent line, other arc
        #may need it's constraint deleted and reapplied to tangent line

        #NOTE - It should be acceptable to bind only one coincident endpoint
        #to the tangent line, then tangentially bind the other arc endpoint
        #to the first

        #2.  Arc bound to tangent line.  Tangent line should be bound
        #by coincident constraint to the arc end point.  Delete coincident
        #constraint and leave it.

        #delete the constraint on the point we're about to move
################

        #get all attached constraints and geometry attached to the point
        arc_vertex = geo_dict["arc"].get_points()[vertex_index]

        attached = geo_dict["arc"].match_by_vertex(arc_vertex)

        #delete existing constraints first
        for _a in attached:

            if _a.type != Sketcher.Constraint:
                geo_dict["adjacent"] = _a

            self.sketch.delConstraint(_a.index)

        App.ActiveDocument.recompute()

        return geo_dict

    def _reconstrain(self, geo_dict, vertex_index):
        """
        Reconstrains existing geometry previously attached to the
        previous arc end point to the new arc end poin

        Arguments:
        geo_dict - Dictionary of relevant geometry in SketchElements

        Returns:
        Nothing
        """

        #test to determine if there is an arc in the geometry dictionary
        #if so, the arc's vertex in the dictionary will need to be bound
        #to the end tangent, which is the created tangent.
        if geo_dict.has_key("arc"):
            
            arc = geo_dict["arc"]

            if vertex_index == -1:
                return

            new_arc = geo_dict["new_arc"]

            arc_point = arc.get_points[vertex_index]

            arc_start = new_arc.get_points[0]
            arc_end = new_arc.get_points[1]

            #if the end point is closer to the adjusted arc than the start
            #point is, swap them
            if arc_end.sub(arc_point).Length < arc_start.sub(arc_point).Length:

                arc_start, arc_end = arc_end, arc_start

            #build tangent constraints for new arc
            tan_constr_1 = Sketcher.Constraint("tangent", new_arc.index, \
            arc_start, arc.index, vertex_index)

            tan_constr_2 = Sketcher.Constraint("Tangent", new_arc.index, \
            arc_end, geo_dict["end_tangnet"].index)

            #add tangent constraints to the sketch

        return

    def _adjust_curve(self, geo_dict, vertex_index, factor):
        """
        Adjusts the length of the arc by the factor value.

        Arguments:
        geo_dict - The dictionary of selected geometry in SketchElements
        factor - The adjustment factor

        Returns:
        The geometry dictionary with the adjusted arc as an ElementContainer
        object.
        """

        #get references to objects and values we're going to use
        arc = geo_dict["arc"]
        delta_angle = arc.as_arc2d().sweep_angle * factor

        #calculate the parameter for the point's new location
        _u = arc.get_element().FirstParameter + delta_angle

        if vertex_index == 1:
            _u = arc.get_element().LastParameter - delta_angle

        point = arc.get_element().value(_u)

        #move the point, update the dictionary, and return
        self.sketch.movePoint(arc.index, vertex_index + 1, point, 0)

        App.ActiveDocument.recompute()

        geo_dict["arc"].index = arc.index

        _x = geo_dict["arc"].get_element().toShape()

        return geo_dict

    def _get_constrained_vertex(self, constraint):
        """
        Given a dictionary of an arc and two tangents, return the
        vertex index of the arc which is constrained by the start tangent

        Arguments:
        constraint - a constraint as an ElementContainer

        Returns:
        index of constrained arc vertex to start tangent
        """
        result = constraint.get_element().FirstPos

        if result == 0:
            result = constraint.get_element().SecondPos

        return result - 1

    def _generate_new_back_tangent(self, geo_dict, vertex_index):
        """
        Generates a new back tangent based upon the passed
        arc and adjoining back tangents

        Arguments:
        vertex_index - the index of the arc vertex that is to be adjusted
        geo_dict - Geometry dictionary

        Returns:
        Element Container containing reference and index to new
        back tangent
        """

        arc = geo_dict["arc"]
        start_tangent = geo_dict["start_tangent"]
        end_tangent = geo_dict["end_tangent"]

        arc_2d = arc.as_arc2d()

        #get the tangent vector and the curve point it passes through
        tan_vec = arc.get_element().tangent(arc_2d.parameters[vertex_index])[0]
        arc_point = arc.get_points()[vertex_index]

        #create the line which describes the new tangent line
        new_tan_line = GeoObj.Line2d(arc_point, direction = tan_vec)

        #set the new tangent line's start end end points to the
        #intersection of the new tangent line and the existing tangents
        new_tan_line.start_point = \
            new_tan_line.intersect(start_tangent.as_line2d())

        new_tan_line.end_point = \
            new_tan_line.intersect(end_tangent.as_line2d())

        #create the new geometry, add it to the document, and return the
        #geometry as a SketchElement
        new_tangent = new_tan_line.to_line_segment()

        new_tan_idx = self.sketch.addGeometry(new_tangent, True)

        App.ActiveDocument.recompute()

        #apply constraints to new tangent, binding it to the other tangents
        sources = [start_tangent, end_tangent]

        for i in range(0,2):
            constraint = Sketcher.Constraint("PointOnObject", \
            new_tan_idx, i+1, sources[i].index)

            self.sketch.addConstraint(constraint)

        App.ActiveDocument.recompute()

        #create constraint to bind curve end point to new tangent
        constraint = Sketcher.Constraint("Tangent", arc.index,\
            vertex_index + 1, new_tan_idx)

        self.sketch.addConstraint(constraint)

        App.ActiveDocument.recompute()

        return skel.SketchGeometry(self.sketch, new_tan_idx)

    def _get_tangents(self, selection):
        """
        Get the back tangents associated with the selected arc.
        If no arc is selected, returns the original selection

        Arguments:
        selection - The selected geometry as a SketchElement list

        Returns:
        Dictionary of SketchElements containing the tangents and arc
        """
        result = {"arc": None, \
                "start_tangent": None, \
                "end_tangent": None, \
                "constraint": None}

        #iterate the selected elements and sort them accordingly
        for sel in selection:

            if type(sel.get_element()) == Part.ArcOfCircle:
                result["arc"] = sel
            else:
                if result["start_tangent"] == None:
                    result["start_tangent"] = sel
                else:
                    result["end_tangent"] = sel

        #quit early if two back tangents are already selected
        #or if no arc is selected, but a second back tangent is not found
        if result["arc"] == None:
            return result

        #get the geometry attached to the arc
        attached_geo = result["arc"].match_attached_geometry()

        #iterate, saving the Part.LineSegment with the unique index
        for geo in attached_geo:

            if geo.index != result["start_tangent"].index:
                if geo.type == Part.LineSegment:
                    result["end_tangent"] = geo
                    break
        
        return result

    def _validate_selection(self):
        """
        Validates the selected geometry as either construction line segments
        or arcs, ensuring they are constrained to each other properly.

        Arguments:

        None

        Returns:

        ElementContainer List of selection geometry and binding constraint.
        """

        selection = GeoUtils.get_selection(self.sketch)

        if not self._validate_selection_geometry(selection):
            self._notify_error("Invalid Geometry")
            return None

        constraint_list = self._validate_selection_constraints(selection)

        if constraint_list == []:
            self._notify_error("Invalid Constraint")
            return None

        constraint_list = self._validate_selection_bindings(selection,\
        constraint_list)

        if constraint_list == []:
            self._notify_error("Invalid Constraint")
            return None
            
        
        return selection + constraint_list
    
    def _validate_selection_bindings(self, selection, constraints):
        """
        Validates the constraints which bind the selection geometry.

        Arguments:
        selection - A SketchElement list of the selection geometry
        constraints - A SketchElement list of the Sketcher.Constraints

        Returns:
        An SketchElement list of the binding constraints
        """

        result = []

        for constraint in constraints:

            #test for proper connections
            are_connected = False

            for sel in selection:

                are_connected = \
                    (constraint.get_element().First == sel.index) or \
                    (constraint.get_element().Second == sel.index)

                if not are_connected:
                    break

            #if the constraint binds the selected geometry,
            #append it to the selection list as a SketchElement
            if are_connected:
                result.append(constraint)
                break                

        return result

    def _validate_selection_constraints(self, selection):
        """
        Determines the types of constraints used to bind the selected
        geometry.

        Arguments:
        selection - Selected geometry passed as ElementContainer list

        Returns:
        ElementContainer List of valid constraint types
        """
        #test for connected geometry
        rng = range(0, self.sketch.ConstraintCount)
        
        two_back_tangents = (type(selection[0].get_element())==Part.LineSegment) and \
            (type(selection[1].get_element())==Part.LineSegment)

        result = []

        for i in rng:

            constraint = self.sketch.Constraints[i]

            #Tangent, Coincident, and PointOnObject constraints are valid
            #Curves are tangentially constrained.  Line segments may be
            #coincident or PointOnObject

            is_valid = constraint.Type=="Tangent" and not two_back_tangents

            if not is_valid:

                is_valid = (constraint.Type in ["Coincident", "PointOnObject"])\
                and two_back_tangents

            #skip to next constraint if type check fails
            if not is_valid:
                continue

            result.append (skel.SketchConstraint(self.sketch, i))
        
        return result

    def _validate_selection_geometry(self, selection):
        """
        Validates the selected geometry.

        Arguments:

        selection - selected geometry as SketchElements

        Returns:
        true / false if valid / invalid
        """

        sel_count = len(selection)

        if sel_count == 0:
            return True

        #only two geometry may be selected
        if sel_count != 2:
            self._notify_error("Selection")
            return False

        #iterate selected geometry ensuring:
        #1- two line segments or one line segment and one arc are selected
        #2 -selected line segments are in construction mode
        valid_geo = True
        last_type = None
        is_two_lines = True

        for geo in selection:

            geo_type = type(geo.get_element())

            if geo_type == Part.LineSegment:
                valid_geo = geo.get_element().Construction

            elif geo_type == Part.ArcOfCircle:
                is_two_lines = False
                valid_geo = (last_type != Part.ArcOfCircle)

            else:
                valid_geo = False

            if not valid_geo:
                break

            last_type = geo_type

        #test to ensure endpoints intersect if two tangents are selected
        if valid_geo and is_two_lines:
            if selection[0].is_coincident(selection[1].index):
                result = selection[0].match_attached_geometry()

                for item in result:
                    if item.type == Part.ArcOfCircle:
                        valid_geo = False
                        self._notify_error("Attached Geometry")
                        break
                
                valid_geo = True

        return valid_geo

    def _notify_error(self, error_type):

        title = error_type + " Error"
        message = "UNDEFINED ERROR"

        if error_type == "Selection":
            message = "Select two adjacent back tangents, two adjacent curves, \
            or an adjacent back tangent and curve to place curve."

        elif error_type == "Attached Geometry":
            message = "Selected elements have attached arc."

        elif error_type == "Invalid Geometry":
            message = "Selected elements have incorrect geometry. \
            Select either line segments or arcs.  Line segments must be \
            construction mode."

        elif error_type == "Invalid Constraint":
            message = "Selected geometry are not properly constrained."

        elif error_type == "Not Coincident":
            message = "Selected geometry do not intersect."

        elif error_type == "No Arc":
            message = "Expected an arc to be selected."

        QtGui.QMessageBox.critical(None, title, message)

Gui.addCommand('InsertCurve',InsertCurve()) 
