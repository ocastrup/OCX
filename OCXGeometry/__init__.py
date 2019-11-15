#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.
from pathlib import Path

import OCC
import numpy
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.TCollection import TCollection_ExtendedString, TCollection_AsciiString
from OCC.Core.TDataStd import TDataStd_Name
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Solid, TopoDS_Face, TopoDS_Shape, TopoDS_Wire, TopoDS_Compound
from OCC.Core.gp import gp_Vec
from OCC.Extend.DataExchange import read_iges_file, read_step_file
from OCC.Core.XCAFDoc import (XCAFDoc_DocumentTool_ShapeTool,
                              XCAFDoc_DocumentTool_ColorTool,
                              XCAFDoc_DocumentTool_LayerTool,
                              XCAFDoc_DocumentTool_MaterialTool)
from OCC.Core.STEPCAFControl import STEPCAFControl_Writer

import OCCWrapper
import OCXCommon
import OCXParser
from OCXCommon import Point3D, Vector3D


class GeometryBase:
    def __init__(self):
        self.done = False

    def IsDone(self) -> bool:
        return self.done


class OCXGeometry(GeometryBase):
    def __init__(self, model, dict,  log=False):
        super().__init__()
        # Create a BRep solid of the object
        self.logging = log
        self.dict = dict
        self.model = model
        self.body = TopoDS_Solid
        self.face = TopoDS_Face


    def Solid(self) -> TopoDS_Solid:
        return self.body

    def Face(self) -> TopoDS_Face:
        return self.face

    def createGeometry(self, solid=False):
        # Loop over all brackets and create a Brep body if solid=True, else return the face
        shapes = []
        for br in self.model.getBrackets:
            OCXCommon.LogMessage(br, self.logging)
            mkgeom = CreateShape(self.model, br, self.dict, solid, self.logging)  # Init the creator
            mkgeom.create()  # Create the Brep
            if mkgeom.IsDone():
                if solid:
                    shapes.append(mkgeom.solid)
                else:
                    shapes.append(mkgeom.face)
        # Loop over all plates and create a Brep body if solid=True, else return the face
        for plate in self.model.getPlates:
            OCXCommon.LogMessage(plate, self.logging)
            mkgeom = CreateShape(self.model, plate, self.dict, solid, self.logging)  # Init the creator
            mkgeom.create()  # Create the Brep
            if mkgeom.IsDone():
                if solid:
                    shapes.append(mkgeom.solid)
                else:
                    shapes.append((mkgeom.face))
        # TODO: Create stiffeners geometry
        return shapes

    def createPartGeometry(self, guid, solid=False):
        # Create a Brep body if solid=True, else return the face for the part with GUIDRef=guid
        object = self.model.getObject(guid)
        shape = TopoDS_Shape
        if not object == None:  # If for some reason we dont find an object
            # Create the object shape
            mkgeom = CreateShape(self.model, object, self.dict, solid, self.logging)  # Init the creator
            mkgeom.create()  # Create the Brep
            if mkgeom.IsDone():
                if solid:
                    shape = mkgeom.Solid()
                else:
                    shape = mkgeom.Face()
            else:
                print('No OCX part with GUIDRef {}'.format(guid))
        return shape

    def externalGeometry(self):
        # Read the iges external geometry for each plate and return the shapes
        # Loop over all objects
        shapes = []
        for plate in self.model.getPlates:
            LogMessage(plate, self.logging)
            extg = ExternalGeometry(self.model, plate, self.dict, self.logging)  # Init the creator
            extg.readExtGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for stiffener in self.model.getStiffeners:
            LogMessage(stiffener, self.logging)
            extg = ExternalGeometry(self.model, stiffener, self.dict, self.logging)  # Init the creator
            extg.readExtGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for br in self.model.getBrackets:
            LogMessage(br, self.logging)
            extg = ExternalGeometry(self.model, br, self.dict, self.logging)  # Init the creator
            extg.readExtGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for pil in self.model.getPillars:
            LogMessage(pil, self.logging)
            extg = ExternalGeometry(self.model, pil, self.dict, self.logging)  # Init the creator
            extg.readExtGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        return shapes

    def externalGeometryAssembly(self):
        # Create a TDoc holding the assembly of structure parts with external geometry. When assembled, write the STEP file
        # Initialize the  writer
        shapes = []
        step_writer = STEPCAFControl_Writer()
        step_writer.SetNameMode(True)
        step_writer.SetPropsMode(True)
        # create the handle to a document
        doc = TDocStd_Document(TCollection_ExtendedString(\ocx-doc\))
        # Get root assembly
        shape_tool = XCAFDoc_DocumentTool_ShapeTool(doc.Main())
        shape_tool.SetAutoNaming(False)
        l_colors = XCAFDoc_DocumentTool_ColorTool(doc.Main())
        l_layers = XCAFDoc_DocumentTool_LayerTool(doc.Main())
        l_materials = XCAFDoc_DocumentTool_MaterialTool(doc.Main())
        aBuilder = BRep_Builder()
        # Loop over all Panels
        panelchildren = []
        for panel in self.model.getPanels:
            OCXCommon.LogMessage(panel, self.logging)
            guid = self.model.getGUID(panel)
            children = self.model.getPanelChildren(guid)
            panelchildren = panelchildren + children
            # Build the Panel compound
            compound = TopoDS_Compound()
            aBuilder.MakeCompound(compound)
            label = shape_tool.AddShape(compound)
            pname = panel.get('name')
            tname = TDataStd_Name()
            tname.Set(TCollection_ExtendedString(pname))
            label.AddAttribute(tname)
            for child in children:
                object = self.model.getObject(child)
                name = object.get('name')
                extg = ExternalGeometry(self.model, object, self.dict, self.logging)  # Init the creator
                extg.readExtGeometry()  # Read the Brep
                if extg.IsDone():
                    aBuilder.Add(compound, extg.Shape())
                    tname = TDataStd_Name()
                    label = shape_tool.AddShape(extg.Shape())
                    tname.Set(TCollection_ExtendedString(name))
                    label.AddAttribute(tname)
        # Root brackets
        compound = TopoDS_Compound()
        aBuilder.MakeCompound(compound)
        label = shape_tool.AddShape(compound)
        tname = TDataStd_Name()
        tname.Set(TCollection_ExtendedString('Brackets'))
        label.AddAttribute(tname)
        for br in self.model.getBrackets:
            guid = self.model.getGUID(br)
            name = br.get('name')
            if guid not in panelchildren:
                extg = ExternalGeometry(self.model, br, self.dict, self.logging)  # Init the creator
                extg.readExtGeometry()  # Read the Brep
                if extg.IsDone():
                    aBuilder.Add(compound, extg.Shape())
                    tname = TDataStd_Name()
                    label = shape_tool.AddShape(extg.Shape())
                    tname.Set(TCollection_ExtendedString(name))
                    label.AddAttribute(tname)
        # Root plates
        compound = TopoDS_Compound()
        aBuilder.MakeCompound(compound)
        label = shape_tool.AddShape(compound)
        tname = TDataStd_Name()
        tname.Set(TCollection_ExtendedString('Plates'))
        label.AddAttribute(tname)
        for pl in self.model.getPlates:
            guid = self.model.getGUID(pl)
            name = pl.get('name')
            if guid not in panelchildren:
                extg = ExternalGeometry(self.model, pl, self.dict, self.logging)  # Init the creator
                extg.readExtGeometry()  # Read the Brep
                if extg.IsDone():
                    aBuilder.Add(compound, extg.Shape())
                    tname = TDataStd_Name()
                    label = shape_tool.AddShape(extg.Shape())
                    tname.Set(TCollection_ExtendedString(name))
                    label.AddAttribute(tname)
        # Root pillars
        compound = TopoDS_Compound()
        aBuilder.MakeCompound(compound)
        label = shape_tool.AddShape(compound)
        tname = TDataStd_Name()
        tname.Set(TCollection_ExtendedString('Pillars'))
        label.AddAttribute(tname)
        for pil in self.model.getPillars:
            guid = self.model.getGUID(pil)
            name = pil.get('name')
            if guid not in panelchildren:
                extg = ExternalGeometry(self.model, pil, self.dict, self.logging)  # Init the creator
                extg.readExtGeometry()  # Read the Brep
                if extg.IsDone():
                    aBuilder.Add(compound, extg.Shape())
                    tname = TDataStd_Name()
                    label = shape_tool.AddShape(extg.Shape())
                    tname.Set(TCollection_ExtendedString(name))
                    label.AddAttribute(tname)
        step_writer.Perform(doc, TCollection_AsciiString(self.model.ocxfile.stem + '.stp'))
        return

    def externalPartGeometry(self, guid):
        # Read the iges external geometry for part with GUIDRef=guid
        # Find the object
        shape = None
        object = self.model.getObject(guid)
        if not object == None:
            LogMessage(object, self.logging)
            extg = ExternalGeometry(self.model, object, self.dict, self.logging)  # Init the creator
            extg.readExtGeometry()  # Read the iges shape
            if extg.IsDone():
                shape = extg.Shape()
        return shape

class CreateShape(GeometryBase):
    def __init__(self, model, object, dict, solid: bool,log: bool):
        super().__init__()
        self.model = model
        self.object = object
        self.dict = dict
        self.logging = log
        self.solid = solid

    # Execute the Brep creation
    def create(self):
        # Step 1: Create a face from the object outer contour
        mkface = FaceFromContour(self.object, self.dict, self.logging)
        face = mkface.create()
        if mkface.IsDone():
            # Step 2: create a body from the face
            if self.solid:
                mkbody = SolidFromFace(self.model, face, self.object, self.dict, self.logging)
                mkbody.create()
                if mkbody.IsDone():
                    self.body = mkbody.Shape()
                    self.done = True
                else:
                    self.done = False
            else:
                self.face = face
                self.done = True
        else:
            self.done = False
        return


class FaceFromContour(GeometryBase):
    def __init__(self, object, dict, log=False):
        super().__init__()
        self.object = object
        self.dict = dict
        self.face = TopoDS_Face
        self.logging = log

    def create(self) -> TopoDS_Face:
        contour = OuterContour(self.object, self.dict, self.logging)
        wire = contour.countourAsWire()
        # Create the outer wire
        if contour.IsDone():
            # Create the face from the outer contour
            mkface = OCCWrapper.OccFaceFromWire(wire)
            if mkface.IsDone():
                self.done = True
                self.face = mkface.Face()
        #            else:
        #               BrepError(self.object, mkface)
        #        else:
        #            BrepError(self.object, wire)
        return self.face


class SolidFromFace(GeometryBase):
    def __init__(self, model, face, object, dict, log):
        super().__init__()
        self.object = object
        self.dict = dict
        self.face = face
        self.solid = TopoDS_Solid
        self.logging = log
        self.model = model

    def create(self):
        if self.face_is_plane(self.face):
            # Create the extrusion vector from the UnboundedSurface and the material direction
            unb = UnboundedGeometry(self.model, self.object, self.dict, self.logging)
            surf = unb.surface()
            normal = numpy.array([0, 0, 0])
            if surf.tag == self.dict['plane3d']:
                plane = OCXParser.ParametricPlane(surf, self.dict, self.model)
                normal = plane.normal
            elif surf.tag == self.dict['gridref']:
                ref = surf.get(self.dict['guidref'])
                normal = self.model.frameTableNormal(ref)
            # Get the sweep length as the object thickness
            pm = self.object.find(self.dict['platematerial'])
            material = OCXCommon.Material(self.model, self.object, pm, self.dict, self.logging)
            th = material.thickness()
            # Create the solid
            #            mksolid = OCCWrapper.OccMakeSolidPrism(self.face)
            v = th * normal
            aVec = gp_Vec(v[0], v[1], v[2])
            self.solid = BRepPrimAPI_MakePrism(self.face, aVec).Shape()
            #            if mksolid.IsDone():
            #                mksolid.sweep(normal, thick)
            #                self.solid = mksolid.Value()
            self.done = True
        else:
            # TODO: Create solid from complex surface
            self.done = False

    def face_is_plane(self, face):
        temp = OCCWrapper.OccMakeSolidPrism(self.face)
        return temp.face_is_plane(face)

    def Shape(self) -> TopoDS_Shape:
        return self.solid


class NURBS(GeometryBase):
    def __init__(self, nurbs, dict):
        super().__init__()
        self.edge = None
        #
        # Function to retrieve the coordinates from 'CircumArc3D'
        # RETURNS:   An Edge constructed from the arc
        #
        id = nurbs.get('id')
        props = nurbs.find(dict['nurbsproperties'])
        nCpts = int(props.get('numCtrlPts'))
        nKnts = int(props.get('numKnots'))
        degree = int(props.get('degree'))
        form = props.get('form')
        if form == 'Open':
            periodic = False
        else:
            periodic = True
        rational = props.get('isRational')
        scope = props.get('scope')
        knotv = nurbs.find(dict['knotvector'])
        knotvalues = knotv.get('value')
        knots = knotvalues.split()
        knotvector = []
        for k in knots:
            knotvector.append(float(k))
        pts = nurbs.findall('.//' + dict['point3d'])  # Finds all Point3D under the NURBS3D
        controlp = []
        for pt in pts:
            p = Point3D(pt, dict)
            controlp.append(p.GetPoint())
            # MathematicaWrapper.MathNURBS('NURBS3D'+id, controlp, knotvector, degree)
        edge = OCCWrapper.OccNURBS(controlp, knotvector, len(knotvector), degree,
                                   periodic)  # OccNurbs returns an edge constructed from the nurbs curve
        if edge.IsDone():
            self.done = True
            self.edge = edge.Edge()

    def Value(self):
        return self.edge


class Circle(GeometryBase):
    def __init__(self, circle, dict):
        super().__init__()
        self.wire = TopoDS_Wire
        #
        # RETURNS:   An Edge constructed from the circle
        #
        diameter = circle.find(dict['diameter'])
        unit = OCXCommon.OCXUnit(dict)
        d = unit.numericValue(diameter)
        center = circle.find(dict['center'])
        p = Point3D(center, dict)
        normal = circle.find(dict['normal'])
        vec = Vector3D(normal, dict)
        c = p.GetPoint()
        wire = OCCWrapper.OccCircle(c, vec.GetVector(), d / 2)  # OccCircle returns the wire constructed from the curve
        if wire.IsDone():
            self.done = True
            self.wire = wire.Wire()

    #        else:
    #            BrepError(circle, wire)

    def Value(self) -> TopoDS_Wire:
        return self.wire


class CircumCircle(GeometryBase):
    def __init__(self, arc, dict):
        super().__init__()
        self.wire = TopoDS_Wire
        #
        # Function to retrieve the coordinates from 'CircumArc3D'
        # RETURNS:   An Edge constructed from the arc
        #
        start = arc.find(dict['startpoint'])
        intermediate = arc.find(dict['intermediatepoint'])
        end = arc.find(dict['endpoint'])
        p1 = Point3D(start, dict)
        p2 = Point3D(intermediate, dict)
        p3 = Point3D(end, dict)
        gp1 = p1.GetPoint()
        gp2 = p2.GetPoint()
        gp3 = p3.GetPoint()
        wire = OCCWrapper.OccCircleFrom3Points(gp1, gp2, gp3)  #
        if wire.IsDone():
            self.done = True
            self.wire = wire.Wire()

    def Value(self) -> TopoDS_Wire:
        return self.wire

# Return the OuterContour as a closed wire
class OuterContour(GeometryBase):
    def __init__(self, object, dict, log=False):
        super().__init__()
        self.dict = dict
        self.object = object
        self.wire = TopoDS_Wire
        self.logging = log
        self.npoints = 100

    def countourAsWire(self) -> TopoDS_Wire:
        # OuterContour
        outercontour = self.object.find(self.dict['outercontour'])
        children = outercontour.findall('*')  # Retrieve all children
        edges = []
        for child in children:
            # if child.tag == self.dict['ellipse3d']:
            # edge = self.ellipse(child)
            tag = child.tag
            id = child.get('id')
            if self.logging:
                print('Parsing: ', tag, ' with id: ', id)
            if child.tag == self.dict['circumcircle3d']:  # Closed contour
                wire = CircumCircle(child, self.dict)
                if wire.IsDone():
                    self.wire = wire.Value()
                    self.done = True
            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = Circle(child, self.dict)
                if closed.IsDone():
                    self.wire = closed.Value()
                    self.done = True
            elif child.tag == self.dict['circumarc3d']:
                edge = CircumArc(child, self.dict)
                if edge.IsDone():
                    edges.append(edge.Value())
            elif child.tag == self.dict['line3d']:
                edge = Line3D(child, self.dict)
                if edge.IsDone():
                    edges.append(edge.Value())
            elif child.tag == self.dict['compositecurve3d']:
                composite = CompositeCurve(child, self.dict, self.logging)
                edges.append(composite.countourAsEdges())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)

            elif child.tag == self.dict['nurbs3d']:
                edge = NURBS(child, self.dict)
                if edge.done:
                    edges.append(edge.Value())
            else:
                print('OuterContour: Unknown child ', child.tag)
        if len(edges) > 0:
            mkwire = OCCWrapper.OccWire(edges)
            if mkwire.IsDone():
                self.wire = mkwire.Wire()
                self.done = True
        #            else:
        #                BrepError(self.object, mkwire)
        return self.wire

    def curveResolution(self, res: int):
        self.npoints = res

    def contourAsPoints(self) -> numpy.array:
        # Create the wire
        wire = self.countourAsWire()
        pts = []
        if self.done:
            # Loop over the wire to get the edges
            edge_explorer = TopExp_Explorer(wire, TopAbs_EDGE)
            while edge_explorer.More():
                edge = OCC.Core.TopoDS.topods_Edge(edge_explorer.Current())
                curve = edge.Value()
                # TODO: Get the coordinates from the edge curve
                edge_explorer.Next()
        return pts


class Line3D(GeometryBase):
    def __init__(self, line, dict):
        super().__init__()
        #
        # Function to construct an edge from the coordinates from 'Line3D'
        # RETURNS:   The (x,y,z) of StartPoint and EndPoint
        #
        startpoint = line.find(dict['startpoint'])
        pt3d = Point3D(startpoint, dict)
        p1 = pt3d.GetPoint()
        endpoint = line.find(dict['endpoint'])
        pt3d = Point3D(endpoint, dict)
        p2 = pt3d.GetPoint()
        edge = OCCWrapper.OccEdge(p1, p2)
        if edge.IsDone():
            self.done = True
            self.edge = edge.Value()

    def Value(self):
        return self.edge


class ExternalGeometry(GeometryBase):
    def __init__(self, model, object, dict, log=False):
        super().__init__()
        # External geometry reference
        self.object = object
        self.logging = log
        self.dict = dict
        self.model = model
        self.ocxfile = self.model.ocxfile

    def readExtGeometry(self):
        self.shape = TopoDS_Shape
        extg = self.object.find(self.dict['externalgeometryref'])
        if extg == None:
            if self.logging == True:
                OCXCommon.Message(self.object, 'has no external geometry')
        else:
            extfile= str(extg.get(self.dict['externalref']))  # Relative path to the input ocxfile
            extfile= extfile.replace('\\','/') #Fix for UNIX systems
            gfile = Path(extfile)
            # Build the full file path
            file = self.ocxfile.parent
            for part in gfile.parts:
                file = file / part
            filename = file.resolve()
            format = extg.get('geometryFormat')
            if filename.is_file():
                if format == 'STEP':
                    self.shape = read_step_file(str(filename))
                    self.done = True
                elif format == '.igs': # TODO: S3D export must change to 'IGES'
                    self.shape = read_iges_file(str(filename))
                    self.done = True
                else:
                    print('Unknown geometry format')
            else:
                print(file + ' not exist')
        return

    def Shape(self) -> TopoDS_Shape:
        return self.shape


class CircumArc(GeometryBase):
    def __init__(self, arc, dict):
        super().__init__()
        self.edge = None
        #
        # Function to retrieve the coordinates from 'CircumArc3D'
        # RETURNS:   An Edge constructed from the arc
        #
        start = arc.find(dict['startpoint'])
        intermediate = arc.find(dict['intermediatepoint'])
        end = arc.find(dict['endpoint'])
        p1 = Point3D(start, dict)
        p2 = Point3D(intermediate, dict)
        p3 = Point3D(end, dict)
        gp1 = p1.GetPoint()
        gp2 = p2.GetPoint()
        gp3 = p3.GetPoint()
        edge = OCCWrapper.OccArc(gp1, gp2, gp3)  # OccArc returns an edge constructed from the curve
        if edge.IsDone():
            self.done = True
            self.edge = edge.Edge()

    def Value(self):
        return self.edge


    def spline(self, coords, open):
        #
        # Function to interpolate a native 3D curve
        # INPUT:
        # coords: Array of (x,y,z) positions of target curve
        # open: True if the target curve is non-periodic
        # RETURNS:   Array of (x,y,z) positions interpolating the curve type
        #
        from scipy.interpolate import CubicSpline  # Pull in the interpolation library
        interpolatingpoints = 10
        knots = numpy.linspace(0, 1, len(coords))
        if open:  # The curve is not periodic
            bc = 'not-a-knot'
        else:
            bc = 'periodic'
        cs = CubicSpline(knots, coords, bc_type=bc)
        xs = numpy.linspace(0, 1, interpolatingpoints)
        return cs(xs)


class CompositeCurve:
    def __init__(self, object, dict, log=False):
        self.dict = dict
        self.object = object
        self.edges = []
        self.logging = log

    def countourAsEdges(self):
        # CompositeCurve
        children = self.object.findall('*')  # Retrieve all children
        for child in children:
            tag = child.tag
            id = child.get('id')
            if self.logging:
                print('Parsing :', tag, ' with id: ', id)
            # if child.tag == self.dict['ellipse3d']:
            # edge = self.ellipse(child)

            if child.tag == self.dict['circumcircle3d']:
                edge = CircumCircle(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = Circle(child, self.dict)
                if closed.IsDone():
                    self.edges.append(closed.Value())

            elif child.tag == self.dict['circumarc3d']:
                edge = CircumArc(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['line3d']:
                edge = Line3D(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)

            elif child.tag == self.dict['nurbs3d']:
                edge = NURBS(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())
            else:
                print('CompositeCurve: Unknown child ', child.tag)
        return self.edges

# Ther can be several closed inner contours, treat differently than OuterContour
class InnerContours:
    def __init__(self, parentface, contour, dictionary: dict, log=True):
        self.closed = False
        self.contour = contour
        self.face = parentface  # The parent face to be cut
        self.edges = []
        self.dict = dictionary
        self.logging = log

    def cutOut(self):  # Returns the parent face cut by all inner contours
        children = self.contour.findall('*')  # Retrieve all children contours
        for child in children:
            tag = child.tag
            id = child.get('id')
            if self.logging:
                print('Parsing: ', tag, ' with id: ', id)
            # TODO: Implement Ellipse curve
            # if child.tag == self.dict['ellipse3d']: # A closed contour
            # edge = self.ellipse(child)
            if child.tag == self.dict['circumcircle3d']:  # A closed contour
                closed = CircumCircle(child, self.dict)
                if closed.IsDone():
                    # Cut out a hole
                    self.face = self.cutFace(self.face, closed.Value())
            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = Circle(child, self.dict)
                if closed.IsDone():
                    # Cut out a hole
                    self.face = self.cutFace(self.face, closed.Value())

            elif child.tag == self.dict['circumarc3d']:
                edge = CircumArc(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['line3d']:
                edge = Line3D(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())
            # TODO: Check for closed contour
            elif child.tag == self.dict['compositecurve3d']:
                composite = CompositeCurve(child, self.dict)
                self.edges.append(composite.countourAsEdges())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)
            # TODO: A nurbs may also be closed?
            elif child.tag == self.dict['nurbs3d']:
                edge = NURBS(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())
            else:
                print('InnerContour: Unknown child ', child.tag)
            # Cut the remaining openings from the set of edges forming a closed contour
            self.face = self.cutFace(self.face, self.edges)
            return self.face

    def cutFace(self, face, contour):
        wire = OCCWrapper.OccWire(contour)
        # Create the face from the inner contour
        if wire.IsDone():
            innerface = OCCWrapper.OccFaceFromWire(wire.Wire())
            if innerface.IsDone():
                cutter = OCCWrapper.OccCutFaces(face, innerface.Face())
                if cutter.IsDone():
                    face = cutter.Face()
        return face

    def IsClosed(self):
        return self.closed