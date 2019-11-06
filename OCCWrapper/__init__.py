#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.
#  pythonocc wrapper classes

import numpy
from OCC.Core.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger

import OCCWrapper


from OCC.Core.gp import gp_Pnt, gp_OX, gp_Vec, gp_Trsf, gp_DZ, gp_Ax2, gp_Ax3, gp_Pnt2d, gp_Dir2d, gp_Ax2d, gp_Pln,\
    gp_Dir
from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment, GC_MakeCircle
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.Geom import Geom_Plane, Geom_CylindricalSurface, Geom_BSplineCurve
from OCC.Core.Geom2d import Geom2d_Ellipse, Geom2d_TrimmedCurve
from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform, BRepBuilderAPI_NurbsConvert)
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_BooleanOperation, BRepAlgoAPI_Cut
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeThickSolid, BRepOffsetAPI_ThruSections
from OCC.Core.BRepLib import breplib
from OCC.Core.BRep import BRep_Tool_Surface, BRep_Builder
from OCC.Core.TopoDS import topods, TopoDS_Compound, TopoDS_Face, TopoDS_Edge, TopoDS_Wire, TopoDS_Solid, TopoDS_Shape
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_HCurve
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCC.Core.BRepFill import BRepFill_CurveConstraint
from OCC.Display.SimpleGui import init_display
from OCC.Core.GeomAbs import GeomAbs_C0
from OCC.Core.GeomLProp import GeomLProp_SLProps
from OCC.Core.GeomPlate import (GeomPlate_BuildPlateSurface, GeomPlate_PointConstraint,
	                            GeomPlate_MakeApprox)
from OCC.Core.ShapeAnalysis import ShapeAnalysis_Surface
from OCC.Core.BRepFill import BRepFill_Filling

from OCC.Extend.TopologyUtils import TopologyExplorer, WireExplorer
from OCC.Extend.ShapeFactory import make_face, make_vertex, point_list_to_TColgp_Array1OfPnt
from OCC.Extend.DataExchange import read_iges_file

# OCCWrapper base class
class OccBase:
    def __init__(self):
        self.done = False

    def IsDone(self) -> bool:
        return self.done

# Generic error handler
class OccError:
    def __init__(self, operation: str, object):
        error = object.Error()
        my_type = type(object)
        print('OCC Error in operation {} with type {}: {}'.format(operation,my_type, error))

# Returns an OCC gp_Pnt
class OccPoint:
    def __init__(self, p: numpy ):
        self.gp = gp_Pnt(p[0], p[1],p[2])

    #Return the constructed edge
    def Value(self) -> gp_Pnt:
        return self.gp

# Returns an OCC gp_Dir
class OccVector:
    def __init__(self, v: numpy ):
        self.vec = gp_Vec(v[0], v[1],v[2])

    #Return the constructed edge
    def Value(self) -> gp_Vec:
        return self.vec

# Construct an edge
class OccEdge(OccBase):
    def __init__(self, p1: numpy, p2: numpy):
        super().__init__()
        self.done = False
        self.edge = None
        gp1 = gp_Pnt(p1[0], p1[1],p1[2])
        gp2 =gp_Pnt(p2[0], p2[1], p2[2])
        edge = BRepBuilderAPI_MakeEdge(gp1, gp2)
        if not edge.IsDone():
            OCCWrapper.OccError('OccEdge', edge)
        else:
            self.done = True
        self.edge = edge.Edge()

    #Return the constructed edge
    def Value(self) -> TopoDS_Edge:
        return self.edge

class OccWire(OccBase):
    def __init__(self, edges):
        super().__init__()
        self.wire = None
        mkwire = BRepBuilderAPI_MakeWire()
        if isinstance(edges, TopoDS_Edge):
            mkwire.Add(edges)
            self.done = True
            self.wire = mkwire.Wire()
        elif len(edges) > 0:
            for edge in edges:
                if isinstance(edge, list):
                     for e in edge:
                        mkwire.Add(e)
                else:
                    mkwire.Add(edge)
            if not mkwire.IsDone():
                OCCWrapper.OccError('OccWire', mkwire)
            else:
                self.done = True
                self.wire = mkwire.Wire()
        return

    def Wire(self) -> TopoDS_Wire:
        return self.wire


class OccPlane:
    def __init__(self, p: numpy, v: numpy):
        self.plane
        gp = OccPoint(p)
        gv = OccVector(v)
        self.plane = Geom_Plane(gp, gv)

    def Value(self) -> gp_Pln:
        return self.plane

class OccFaceFromWire(OccBase):
    def __init__(self, wire: TopoDS_Wire):
        super().__init__()
        mkface = BRepBuilderAPI_MakeFace(wire)
        if not mkface.IsDone():
            OCCWrapper.OccError('OccFaceFromWire',mkface)
        else:
            self.done = True
            self.face = mkface.Face()
        return

    def Face(self) -> TopoDS_Face:
        return self.face

class OccCutFaces(OccBase):
    def __init__(self, base: TopoDS_Face, cut: TopoDS_Face):
        super().__init__()
        self.shape = None
        self.shape = BRepAlgoAPI_Cut(base, cut).Shape()
        self.done = True
        return

    def Face(self) -> TopoDS_Face:
        return self.shape

class OccMakeSolidPrism(OccBase):
    def __init__(self, base: TopoDS_Face):
        super().__init__()
        self.face = base # face must be planar
        self.solid = TopoDS_Solid
        self.done = True

    # Construct solid
    def sweep(self, vec: numpy.array, s: float):
        # Sweep the face in the vec direction the distance s
        svec = vec * s
        aVec = OccVector(svec)
        if self.face_is_plane(self.face):
            mksolid = BRepPrimAPI_MakePrism(self.face, aVec.Value())
            if mksolid.IsDone():
                self.solid = mksolid.Shape()
                self.done = True
            else:
                OccError('MakeSolidPrism', mksolid)
        else:
            OccError('MakeSolidPrism', self)
        return

    def Error(self):
        return 'Base must be planar'

    def Value(self) -> TopoDS_Solid:
        return self.solid

    def face_is_plane(self, face)->bool:
        """
        Returns True if the TopoDS_Shape is a plane, False otherwise
        """
        hs = BRep_Tool_Surface(face)
        downcast_result = Geom_Plane.DownCast(hs)
        # The handle is null if downcast failed or is not possible, that is to say the face is not a plane
        if downcast_result is None:
            return False
        else:
            return True


class OccArc(OccBase):
    def __init__(self, p1: numpy, p2: numpy, p3: numpy):
        # p1: StartPoint
        # p2: EndPoint
        # p3: IntermediatePoint
        super().__init__()
        self.edge = TopAbs_EDGE
        gp1 = OccPoint(p1)
        gp2 = OccPoint(p2)
        gp3 = OccPoint(p3)
        mkarc = GC_MakeArcOfCircle(gp1.Value(), gp3.Value(), gp2.Value()) # Sequence: StartPoint, IntermediatePoint, EndPoint
        if not mkarc.IsDone():
            OCCWrapper.OccError(mkarc.Error())
        else:
            mkedge = BRepBuilderAPI_MakeEdge(mkarc.Value())
            if not mkedge.IsDone():
                OCCWrapper.OccError(mkedge.Error())
            else:
                self.done = True
                self.edge = mkedge.Edge()
        return

    def Edge(self) -> TopoDS_Edge:
        return self.edge


class OccCircle(OccBase):
    def __init__(self, center: numpy.array, normal: numpy.array, radius: float):
        super().__init__()
        self.wire = TopoDS_Wire
        gpCenter = OccPoint(center)
        gpVec = OccVector(normal)
        mkcircle = GC_MakeCircle(gpCenter.Value(), gpVec.Value(), radius)
        if not mkcircle.IsDone():
            OCCWrapper.OccError('OccCircle',mkcircle)
        else:
            mkwire = BRepBuilderAPI_MakeWire(mkcircle.Value())
            if not mkwire.IsDone():
                OCCWrapper.OccError('OccCircle', mkwire)
            else:
                self.done = True
                self.w = mkwire.Wire()
        return

    def Edge(self) -> TopoDS_Wire:
        return self.wire

# Creates a circle from three points
class OccCircleFrom3Points(OccBase):
    def __init__(self, p1: numpy.array, p2: numpy.array, p3: numpy.array):
        # p1, p2, p3: Three points on a circle. Cannot be colinear
        super().__init__()
        self.wire = TopoDS_Wire
        gp1 = OccPoint(p1)
        gp2 = OccPoint(p2)
        gp3 = OccPoint(p3)
        mkcircle = GC_MakeCircle(gp1.Value(), gp3.Value(), gp2.Value())
        if not mkcircle.IsDone():
            OCCWrapper.OccError(type(self), mkcircle)
        else:
            mkwire = BRepBuilderAPI_MakeWire(mkcircle.Value())
            if not mkwire.IsDone():
                OCCWrapper.OccError(type(self), mkwire)
            else:
                self.done = True
                self.wire = mkwire.Wire()
        return

    def Wire(self) -> TopoDS_Wire:
        return self.wire

class OccNURBSFromShape:
    def __init__(self, shape: TopoDS_Shape):
        self.mknurbs = BRepBuilderAPI_NurbsConvert(shape)
        self.shape = shape
        #self.mknurbs.Perform(shape) # Perform the conversion of the shape to a NURBS rep (curve or surface?)

    def Shape(self):
        return self.mknurbs.Shape()

    def IsDone(self) -> bool:
        return self.mknurbs.IsDone()

class OccNURBS(OccBase):
    def __init__(self, controlpoints: numpy, knots: numpy, m: int, degree: int, periodic: bool):
        super().__init__()
        self.edge = TopAbs_EDGE
        array = []
        for pnt in controlpoints:
            p = OccPoint(pnt)
            array.append(p.Value())
        poles = point_list_to_TColgp_Array1OfPnt(array)
        # Normalise the knots and find multiplicities
        multp = OCCWrapper.OccMultiplicities(knots)
        uknots = multp.knots()
        multiplicity = multp.multiplcity()
        knotvector = TColStd_Array1OfReal(1, len(uknots))
        i = 1
        for v in uknots:
            knotvector.SetValue(i, v)
            i = i+1
        mult = TColStd_Array1OfInteger(1, len(multiplicity))
        i = 1
        for m in multiplicity:
            mult.SetValue(i, int(m))
            i = i+1
        mknurbs = Geom_BSplineCurve(poles, knotvector, mult, degree, periodic)
        mkedge = BRepBuilderAPI_MakeEdge(mknurbs)
        if not mkedge.IsDone():
            OCCWrapper.OccError(type(self), mkedge)
        else:
            self.done = True
            self.edge = mkedge.Edge()
        return

    def Edge(self) -> TopoDS_Edge:
        return self.edge


class OccMultiplicities:
    def __init__(self, knots: numpy):
        #Find the unique knots
        u, indices =  numpy.unique(knots, return_index=True)
        #Construct the multiplicity
        n = len(u)
        mult = numpy.zeros(n, dtype = int)
        i = 0
        for ind in indices[:-1]:
            mult[i] = indices[i+1] - ind
            i = i + 1
        mult[-1] = len(knots) - indices[-1]
        self.uknots = u
        self.mult = mult
        return

    def knots(self):
        return self.uknots
    def multiplcity(self):
        return self.mult
