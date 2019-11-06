#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import xml.etree.ElementTree as ET

import OCC
import numpy
import os
import re

from pathlib import Path

from OCC.Core.BRep import BRep_Tool, BRep_Tool_Curve, BRep_Builder
from OCC.Core.ShapeAnalysis import ShapeAnalysis_Curve
from OCC.Core.Visualization import Tesselator
from OCC.Extend.TopologyUtils import TopologyExplorer
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

import OCXParser
import OCXUnits
import OCCWrapper
from OCC.Core.TopoDS import topods, TopoDS_Compound, TopoDS_Face, TopoDS_Edge, TopoDS_Wire, TopoDS_Solid, TopoDS_Shape
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform)

from OCC.Core.gp import gp_Pnt, gp_OX, gp_Vec, gp_Trsf, gp_DZ, gp_Ax2, gp_Ax3, gp_Pnt2d, gp_Dir2d, gp_Ax2d, gp_Pln, \
    gp_Dir
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Extend.DataExchange import read_iges_file

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


class OCXschema:
    # class OCXschema  creates the DOM tree from the OCX xsd schema
    # The class contains the methods for retrieving the OCX elements

    def __init__(self, schema):
        self.parsed = False
        self.filename = schema  # The uri or the file name of the xsd schema
        self.namespace = {}  # The namespaces used by the OCX
        self.attributes = []  # the schema global attributes
        self.elements = []  # the schema global elements
        self.complex = []  # the schema global complex types
        self.version = ''  # The schema version of the parsed xsd
        self.dict = {}  # The schema element dictionary of legal types

        # initialize the name space and parse the xsd

        if self.initNameSpace():
            if not self.parsed:
                self.parseSchema()

    def initNameSpace(self):
        # open the schema file and read the namespaces
        if not os.path.exists(self.filename):
            return False
        fd = open(self.filename, 'r')
        pattern = 'xmlns'
        for line in fd:
            if re.search(pattern, line):
                break  # Break when pattern is found & close the file
        fd.close()

        # Extract the name spaces
        # Example namespace string:   xmlns:xs="http://www.w3.org/2001/XMLSchema"

        ns = re.findall(r'xmlns:\w+="\S+', line)

        # create the name space dict:
        namespace = dict()
        for str in ns:
            k = re.findall(r'xmlns:\w+', str)
            key = re.sub(r'xmlns:', "", k[0])
            v = re.findall(r'=\S+', str)
            value = re.sub(r'[="]+', "", v[0])
            self.namespace[key] = value
        return True

    def getNameSpace(self):
        return self.namespace

    def parseSchema(self):
        if (len(self.namespace)) == 0:
            print('Call method "initNameSpace()"  first')
            return
        # create the OCXdom
        self.tree = ET.parse(self.filename)  # Create the DOM tree
        root = self.tree.getroot()
        # Retreive all global elements
        self.elements = root.findall('xs:element', self.namespace)
        # Retrieve all complex types (we need this as the schemaVersion is part of DocumentBase_T)
        self.complex = root.findall('xs:complexType', self.namespace)
        # Retrieve all global attributes
        self.attributes = root.findall('xs:attribute', self.namespace)

        # Get the schema version
        for cmplx in self.complex:
            name = cmplx.get('name')
            if name == 'DocumentBase_T':
                attr = cmplx.findall('xs:attribute', self.namespace)
                for a in attr:
                    name = a.get('name')
                    if name == 'schemaVersion':
                        self.version = a.get('fixed')
                        break
        # Create the lookup tables
        self.makeDictionary()
        self.parsed = True
        return

    # Create the type dictionary/lookup tables
    def makeDictionary(self):
        self.type = {}

        # Global ocx element and type
        for e in self.elements:
            name = e.get('name')
            typ = e.get('type')
            self.type[name] = typ  # Lookup table for type
        # Global ocx attribute and type
        for e in self.attributes:
            name = e.get('name')
            typ = e.get('type')
            self.type[name] = typ  # Lookup table for type
        # Create static name dictionary
        for e in self.type:
            key = e.lower()
            self.dict[key] = e
        # Wrap namespace declaration
        for e in self.dict:
            value = self.dict[e]
            self.dict[e] = '{' + self.namespace['ocx'] + '}' + value

# class OCXdom  creates the DOM tree from the xml OCX model
# The class contains the methods for retrieving the OCX elements
class OCXdom:

    def __init__(self, model, dictionary: dict, namespace: dict):
        self.filename = model  # The xml file
        self.dict = dictionary  # The namespaces used by the OCX
        self.tree = ET.parse(model)  # Create the DOM tree
        self.root = self.tree.getroot()  # The root node
        self.version = self.root.get('schemaVersion', namespace)  # The schema version of the parsed OCX
        #ocx = self.root.find('ocxXML', namespace)
        #self.header = OCXParser.Header(ocx, self.dict, False)

    def getRoot(self):
        return self.root

    def getVersion(self):
        return self.version

    def getDIctionary(self):
        return self.dict

    def getFileName(self):
        return self.filename

    def getBrackets(self):
        return self.root.findall('.//' + self.dict['bracket'])

    def getPlates(self):
        return self.root.findall('.//' + self.dict['plate'])

    def getPanels(self):
        return self.root.findall('.//' + self.dict['panel'])

    def getMaterials(self):
        return self.root.findall('.//' + self.dict['material'])

    def getStiffeners(self):
        return self.root.findall('.//' + self.dict['stiffener'])

    def getSections(self):
        return self.root.findall('.//' + self.dict['barsection'])

    def getPillars(self):
        return self.root.findall('.//' + self.dict['pillar'])


# Class to parse the OCX model
class OCXmodel:
    def __init__(self, options):
        self.ocxmodel = options.file  # The ocx xml file
        self.ocxschema = options.schema
        self.logging = options.log
        # Create the schema parser and get the namespaces
        sparser = OCXParser.OCXschema(options.schema)
        self.namespace = sparser.getNameSpace()
        self.schema_version = sparser.version
        self.dict = sparser.dict  # The dictionary of parsable ocx elements
        self.guids = {}  # GUID lookup table
        self.frametable = {}  # Frametable dict with guid as key

    # Generic function to retrieve the GUID from an object
    def getGUID(self, object):
        guid = object.get(self.dict['guidref'])
        return guid

    # Import the OCX instances
    def importModel(self):
        # Create the OCXdom
        self.dom = OCXParser.OCXdom(self.ocxmodel, self.dict, self.namespace)
        self.ocxversion = self.dom.version

        # print ocx version and get the root
        self.root = self.dom.getRoot()
        # get the ocxXML header info
        header = OCXParser.Header(self.root, self.dict, self.logging)
            
                             
        print('Parsing OCX model    : ', self.ocxmodel)
        print('OCX version          : ', self.ocxversion)
        if header.hasHeader():
            print('Model name           : ', header.name)
            print('Model timestamp      :  {}'.format(header.ts))
            print('Author               :  {}'.format(header.author))
            print('Originating system   :  {}'.format(header.system))
        if self.ocxversion != self.schema_version:
            print('')
            print('Warning: Version {} of the OCX model is different from the referenced schema version: {}'\
                  .format(self.ocxversion, self.schema_version))
            print('')

        # dom queries
        # Brackets
        self.brackets = self.dom.getBrackets()
        # Plates
        self.plates = self.dom.getPlates()
        # Panels
        self.panels = self.dom.getPanels()
        # Stiffeners
        self.stiffeners = self.dom.getStiffeners()
        # Materials
        self.materials = self.dom.getMaterials()
        # Sections
        self.sections = self.dom.getSections()
        # Pillars
        self.pillars = self.dom.getPillars()
        # Guid lookup table
        self.createGUIDTable()
        # Frame lookup table
        self.createFrameTable()
        # Fine all panel children plates
        self.findPanelChildren()

        print('')
        print('Structure parts in model')
        print('------------------------')
        print('Number of panels     : ', len(self.panels))
        print('Number of plates     : ', len(self.plates))
        print('Number of stiffeners : ', len(self.stiffeners))
        print('Number of pillars    : ', len(self.pillars))
        print('Number of brackets   : ', len(self.brackets))
        print('Number of materials  : ', len(self.materials))
        print('Number of sections   : ', len(self.sections))
        print('')
        return

    def panels(self):
        return self.panels

    def plates(self):
        return self.plates

    def stiffeners(self):
        return self.stiffeners

    def brackets(self):
        return self.brackets

    def materials(self):
        return self.materials

    def sections(self):
        return self.sections

    def pillars(self):
        return self.pillars

    # Find all children structure parts of  the panels and store it's guids  in a dict with the panel guid as key
    def findPanelChildren(self):
        panels = {}
        for panel in self.panels:
            plates = []
            panelguid = self.getGUID(panel)
            children = panel.findall('.//' + self.dict['plate'])
            for child in children:
                childguid = self.getGUID(child)
                plates.append(childguid)
            stiffeners = []
            children = panel.findall('.//' + self.dict['stiffener'])
            for child in children:
                childguid = self.getGUID(child)
                stiffeners.append(childguid)
            brackets = []
            children = panel.findall('.//' + self.dict['bracket'])
            for child in children:
                childguid = self.getGUID(child)
                brackets.append(childguid)
            pillars = []
            children = panel.findall('.//' + self.dict['pillar'])
            for child in children:
                childguid = self.getGUID(child)
                pillars.append(childguid)
            # Add all children
            panels[panelguid] = plates + stiffeners + brackets + pillars
        self.panelchildren = panels

    def getParentPanelGuid(self, sibling: str):
        # Loop over guids in value array
        for panel in self.panelchildren:
            for child in self.panelchildren[panel]:
                if child == sibling:
                    return panel
        return 'NotFound'
    def getPanelChildren(self, panelguid: str):
        if panelguid in self.panelchildren:
            return self.panelchildren[panelguid]
        else:
            print('The Panel with GUIDRef {} does not exist in the OCX model'.format(panelguid))
            return None

    def getObject(self, guid: str):
        if guid in self.guids:
            return self.guids[guid]
        else:
            print('The GUIDRef {} does not exist in the OCX model'.format(guid))
            return None

    def getGUIDs(self):
        return self.guids

    def frameTablePos(self, guid):
        tup = self.frametable[guid]
        return tup[0]

    def frameTableNormal(self, guid):
        tup = self.frametable[guid]
        return tup[1]

    def createGeometry(self, solid=True):
         # Loop over all brackets and create a Brep body if solid=True, else return the face
        shapes = []
        for br in self.brackets:
            LogMessage(br, self.logging)
            mkgeom = OCXParser.CreateGeometry(self, br, self.dict, solid, self.logging)  # Init the creator
            mkgeom.create()  # Create the Brep
            if mkgeom.IsDone():
                if solid:
                    shapes.append(mkgeom.Solid())
                else:
                    shapes.append((mkgeom.Face()))
        # Loop over all plates and create a Brep body if solid=True, else return the face
        for plate in self.plates:
            LogMessage(plate, self.logging)
            mkgeom = OCXParser.CreateGeometry(self, plate, self.dict, solid, self.logging)  # Init the creator
            mkgeom.create()  # Create the Brep
            if mkgeom.IsDone():
                if solid:
                    shapes.append(mkgeom.Solid())
                else:
                    shapes.append((mkgeom.Face()))
#TODO: Create stiffeners geometry
        return shapes

    def createPartGeometry(self, guid, solid=True):
        # Create a Brep body if solid=True, else return the face for the part with GUIDRef=guid
        object = self.getObject(guid)
        shape = TopoDS_Shape
        if not object == None: #If for some reason we dont find an object
            # Create the object shape
            mkgeom = OCXParser.CreateGeometry(self, object, self.dict, solid, self.logging)  # Init the creator
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
        for plate in self.plates:
            LogMessage(plate, self.logging)
            extg = OCXParser.ExternalGeometry(self, plate, self.dict, self.logging)  # Init the creator
            extg.igesGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for stiffener in self.stiffeners:
            LogMessage(stiffener, self.logging)
            extg = OCXParser.ExternalGeometry(self, stiffener, self.dict, self.logging)  # Init the creator
            extg.igesGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for br in self.brackets:
            LogMessage(br, self.logging)
            extg = OCXParser.ExternalGeometry(self, br, self.dict, self.logging)  # Init the creator
            extg.igesGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        for pil in self.pillars:
            LogMessage(pil, self.logging)
            extg = OCXParser.ExternalGeometry(self, pil, self.dict, self.logging)  # Init the creator
            extg.igesGeometry()  # Create the Brep
            if extg.IsDone():
                shapes.append(extg.Shape())
        return shapes

    def externalGeometryAssembly(self):
        # Read the iges external geometry for each panel with sub-parts and return as a compound of shapes
        # Loop over all Panels
        compounds = []
        for panel in self.panels:
            shapes = []
            LogMessage(panel, self.logging)
            guid = self.getGUID(panel)
            children = self.getPanelChildren(guid)
            # Build the resulting compound
            compound = TopoDS_Compound()
            aBuilder = BRep_Builder()
            aBuilder.MakeCompound(compound)
            for child in children:
                object = self.getObject(child)
                extg = OCXParser.ExternalGeometry(self, object, self.dict, self.logging)  # Init the creator
                extg.igesGeometry()  # Create the Brep
                if extg.IsDone():
                    aBuilder.Add(compound, extg.Shape())
            compounds.append(compound)
        return compounds

    def externalPartGeometry(self, guid):
        # Read the iges external geometry for part with GUIDRef=guid
        # Find the object
        shape = None
        object = self.getObject(guid)
        if not object == None:
            LogMessage(object, self.logging)
            extg = OCXParser.ExternalGeometry(self, object, self.dict, self.logging)  # Init the creator
            extg.igesGeometry()  # Read the iges shape
            if extg.IsDone():
                shape = extg.Shape()
        return shape


    def createGUIDTable(self):
        duplicates = []
        guids = {}
        for part in self.plates:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.panels:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.stiffeners:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.brackets:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.sections:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.materials:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        self.guids = guids
        if len(duplicates) > 0:  # Non-unique quids
            print('There are {} non unique guids:'.format(len(duplicates)))
            for part in duplicates:
                name = part.get('name')
                id = part.get('id')
                tag = part.tag
                guid = self.getGUID(part)
                print('Part {} with name {}, id {}  and GUID {} is a duplicate.'.format(tag, name, id, guid))

    def createFrameTable(self):
        frametable = self.root.find('.//' + self.dict['frametables'])
        if not frametable == None:
            tbl = OCXParser.FrameTable(frametable, self.dict, self.namespace, self.logging)
            self.frametable = tbl.frametable

    def logging(self, log):
        self.logging = log

    def get_dict(self):
        return self.dict


class FrameTable:
    def __init__(self, table, dict, namespace, log=False):
        # Create the FrameTable definition as a lookup table with guid as key
        self.table = table
        self.log = log
        self.dict = dict
        self.done = False
        self.frametable = {}
        self.namespace = namespace
        # Create the table
        self.createTable()
        return

    def createTable(self):
        # Get all XRefPlanes
        xrefp = self.table.find(self.dict['xrefplanes'])
        yrefp = self.table.find(self.dict['yrefplanes'])
        zrefp = self.table.find(self.dict['zrefplanes'])
        # X positions
        xrefs = xrefp.findall(self.dict['refplane'])
        for ref in xrefs:
            guid = ref.get(self.dict['guidref'])
            refloc = ref.find(self.dict['referencelocation'])
            unit = OCXUnits.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([pos, 0, 0]), numpy.array([1, 0, 0]))  # tuple of ref pos and plane normal vector
        # Y positions
        yrefs = yrefp.findall(self.dict['refplane'])
        for ref in yrefs:
            guid = ref.get(self.dict['guidref'])
            refloc = ref.find(self.dict['referencelocation'])
            unit = OCXUnits.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([0, pos, 0]), numpy.array([0, 1, 0]))  # tuple of ref pos and plane normal vector
        # Z positions
        zrefs = zrefp.findall(self.dict['refplane'])
        for ref in zrefs:
            guid = ref.get(self.dict['guidref'])
            refloc = ref.find(self.dict['referencelocation'])
            unit = OCXUnits.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([0, 0, pos]), numpy.array([0, 0, 1]))  # tuple of ref pos and plane normal vector
        return

class Header:
    def __init__(self, object, dict, log=False):
        header = object.find(dict['header'])
        if not header == None:
            self.ts = header.get('time_stamp')
            self.name = header.get('name')
            self.author = header.get('author')
            self.org = header.get('organization')
            self.system = header.get('originating_system')
            self.header = True
        else:
            self.header = False

    def timestamp(self):
        return self.ts

    def author(self):
        return self.author

    def name(self):
        return self.name

    def organization(self):
        return self.org

    def originatingSystem(self):
        return self.system

    def hasHeader(self):
        return self.header

class GeometryBase:
    def __init__(self):
        self.done = False

    def IsDone(self) -> bool:
        return self.done

class ExternalGeometry(GeometryBase):
    def __init__(self, model: OCXParser.OCXmodel, object, dict, log=False):
        super().__init__()
        #External geometry reference
        self.object = object
        self.logging = log
        self.dict = dict
        self.model = model
        self.cwd = os.getcwd()

    def igesGeometry(self):
        self.shape = TopoDS_Shape

#TODO: Implement consistent reading of external files and remove hardcoded path
        extg = self.object.find(self.dict['externalgeometryref'])
        if extg == None:
            if self.logging == True: OCXParser.ParseError(self.object, 'has no external geometry')
        else:
            gfile = extg.get(self.dict['externalref'])
            gfile = gfile.replace('\\', '/')
            #format = extg.get(self.dict['geometryformat'])
            file = self.cwd + '/' 'OCX_Models' +'/' + gfile
            igs = Path(file)
            if igs.is_file():
                self.shape = read_iges_file(file)
                self.done = True
            else:
                print(file+ ' not exist')
        return

    def Shape(self)-> TopoDS_Shape:
        return self.shape

class CreateGeometry(GeometryBase):
    def __init__(self, model: OCXParser.OCXmodel, object, dict, solid=True, log=False):
        super().__init__()
        # Create a BRep solid of the object
        self.object = object
        self.logging = log
        self.dict = dict
        self.model = model
        self.solid = solid  # If set to True, make a solid object of the geometry
        self.body = TopoDS_Solid
        self.face = TopoDS_Face

    # Execute the Brep creation
    def create(self):
        # Step 1: Create a face from the object outer contour
        mkface = OCXParser.FaceFromContour(self.object, self.dict, self.logging)
        face = mkface.create()
        if mkface.IsDone():
            # Step 2: create a body from the face
            if self.solid:
                mkbody = OCXParser.SolidFromFace(self.model, face, self.object, self.dict, self.logging)
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

    def Solid(self) -> TopoDS_Solid:
        return self.body

    def Face(self) -> TopoDS_Face:
        return self.face


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
    def __init__(self, model: OCXParser.OCXmodel, face, object, dict, log):
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
            unb = OCXParser.UnboundedGeometry(self.model, self.object, self.dict, self.logging)
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
            material = OCXParser.Material(self.model, self.object, pm, self.dict, self.logging)
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


class Point3D:
    def __init__(self, point, dict):
        # Function to retrieve the coordinates from an 'Point3D' type
        # RETURNS:   the (x,y,z) coordinate
        x = point.find(dict['x'])
        y = point.find(dict['y'])
        z = point.find(dict['z'])
        unit = OCXUnits.OCXUnit(dict)
        xv = unit.numericValue(x)
        yv = unit.numericValue(y)
        zv = unit.numericValue(z)
        self.point = numpy.array([xv, yv, zv])

    def GetPoint(self):
        return self.point


class Vector3D:
    def __init__(self, vec, dict):
        # Function to retrieve the unit vector from an 'Vector3D' type
        # RETURNS:   the (x,y,z) vector
        x = vec.get('x')
        y = vec.get('y')
        z = vec.get('z')
        xv = float(x)
        yv = float(y)
        zv = float(z)
        self.vec = numpy.array([xv, yv, zv])

    def GetVector(self):
        return self.vec


class Line3D(GeometryBase):
    def __init__(self, line, dict):
        super().__init__()
        #
        # Function to construct an edge from the coordinates from 'Line3D'
        # RETURNS:   The (x,y,z) of StartPoint and EndPoint
        #
        startpoint = line.find(dict['startpoint'])
        pt3d = OCXParser.Point3D(startpoint, dict)
        p1 = pt3d.GetPoint()
        endpoint = line.find(dict['endpoint'])
        pt3d = OCXParser.Point3D(endpoint, dict)
        p2 = pt3d.GetPoint()
        edge = OCCWrapper.OccEdge(p1, p2)
        if edge.IsDone():
            self.done = True
            self.edge = edge.Value()

    def Value(self):
        return self.edge


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
            p = OCXParser.Point3D(pt, dict)
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
        unit = OCXUnits.OCXUnit(dict)
        d = unit.numericValue(diameter)
        center = circle.find(dict['center'])
        p = Point3D(center, dict)
        normal = circle.find(dict['normal'])
        vec = OCXParser.Vector3D(normal, dict)
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
        p1 = OCXParser.Point3D(start, dict)
        p2 = OCXParser.Point3D(intermediate, dict)
        p3 = OCXParser.Point3D(end, dict)
        gp1 = p1.GetPoint()
        gp2 = p2.GetPoint()
        gp3 = p3.GetPoint()
        wire = OCCWrapper.OccCircleFrom3Points(gp1, gp2, gp3)  #
        if wire.IsDone():
            self.done = True
            self.wire = wire.Wire()

    def Value(self) -> TopoDS_Wire:
        return self.wire


class ParametricPlane:
    def __init__(self, plane, dict, model: OCXParser.OCXmodel):
        self.edge = None
        self.dict = dict
        self.model = model
        self.origin = [0, 0, 0]
        self.normal = [0, 0, 0]
        #
        # Function to retrieve the Plane3D parameters
        if plane.tag == self.dict['plane3d']:
            origin = plane.find(dict['origin'])
            normal = plane.find(dict['normal'])
            self.origin = OCXParser.Point3D(origin, dict).GetPoint()
            self.normal = OCXParser.Vector3D(normal, dict).GetVector()
        elif plane.tag == self.dict['gridref']:
            guid = plane.get(self.dict['guidref'])
            refplane = model.getObject(guid)

    def normal(self) -> numpy.array:
        return self.normal

    def origin(self) -> numpy.array:
        return self.origin


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
        p1 = OCXParser.Point3D(start, dict)
        p2 = OCXParser.Point3D(intermediate, dict)
        p3 = OCXParser.Point3D(end, dict)
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


# Return the CompositeCurve as edges
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
                edge = OCXParser.CircumCircle(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = OCXParser.Circle(child, self.dict)
                if closed.IsDone():
                    self.edges.append(closed.Value())

            elif child.tag == self.dict['circumarc3d']:
                edge = OCXParser.CircumArc(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['line3d']:
                edge = OCXParser.Line3D(child, self.dict)
                if edge.IsDone():
                    self.edges.append(edge.Value())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)

            elif child.tag == self.dict['nurbs3d']:
                edge = OCXParser.NURBS(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())
            else:
                print('CompositeCurve: Unknown child ', child.tag)
        return self.edges


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
                wire = OCXParser.CircumCircle(child, self.dict)
                if wire.IsDone():
                    self.wire = wire.Value()
                    self.done = True
            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = OCXParser.Circle(child, self.dict)
                if closed.IsDone():
                    self.wire = closed.Value()
                    self.done = True
            elif child.tag == self.dict['circumarc3d']:
                edge = OCXParser.CircumArc(child, self.dict)
                if edge.IsDone():
                    edges.append(edge.Value())
            elif child.tag == self.dict['line3d']:
                edge = OCXParser.Line3D(child, self.dict)
                if edge.IsDone():
                    edges.append(edge.Value())
            elif child.tag == self.dict['compositecurve3d']:
                composite = OCXParser.CompositeCurve(child, self.dict, self.logging)
                edges.append(composite.countourAsEdges())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)

            elif child.tag == self.dict['nurbs3d']:
                edge = OCXParser.NURBS(child, self.dict)
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


# Ther can be several closed inner contours, treat differently as OuterContour
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
                closed = OCXParser.CircumCircle(child, self.dict)
                if closed.IsDone():
                    # Cut out a hole
                    self.face = self.cutFace(self.face, closed.Value())
            elif child.tag == self.dict['circle3d']:  # A closed contour
                closed = OCXParser.Circle(child, self.dict)
                if closed.IsDone():
                    # Cut out a hole
                    self.face = self.cutFace(self.face, closed.Value())

            elif child.tag == self.dict['circumarc3d']:
                edge = OCXParser.CircumArc(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())

            elif child.tag == self.dict['line3d']:
                edge = OCXParser.Line3D(child, self.dict)
                if edge.done:
                    self.edges.append(edge.Value())
            # TODO: Check for closed contour
            elif child.tag == self.dict['compositecurve3d']:
                composite = OCXParser.CompositeCurve(child, self.dict)
                self.edges.append(composite.countourAsEdges())

            # elif child.tag == self.dict['polyline3d']:
            # edge = self.polyline(child)
            # TODO: A nurbs may also be closed?
            elif child.tag == self.dict['nurbs3d']:
                edge = OCXParser.NURBS(child, self.dict)
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


class Material:
    def __init__(self, model: OCXParser.OCXmodel, parent, material, dict, log=False):
        self.dict = dict
        self.logging = log
        self.model = model
        self.material = material
        self.parent = parent

    def thickness(self) -> float:
        thickness = self.material.find(self.dict['thickness'])
        if thickness == None:
            #Assign a default thickness
            th = 0.01
            OCXParser.ParseError(self.parent, 'has no thickness')
        else:
            unit = OCXUnits.OCXUnit()
            th = float(unit.numericValue(thickness))
        return th

class DesignView:
    def __init__(self, model: OCXParser.OCXmodel, parent, view, dict, log=False):
        self.dict = dict
        self.logging = log
        self.model = model
        self.designview = view
        self.parent = parent

    def modelTree(self) -> "void":
# TODO: Implement reading of the product structure

# Return the UnboundedGeometry as a surface
class UnboundedGeometry:
    def __init__(self, model: OCXParser.OCXmodel, object, dict, log=False):
        self.dict = dict
        self.object = object
        self.logging = log
        self.model = model

    def surface(self):
        unbounded = self.object.find(self.dict['unboundedgeometry'])
        if unbounded == None:
            # Find parents unbounded
            guid = self.object.get(self.dict['guidref'])
            parentguid = self.model.getParentPanelGuid(guid)
            parent = self.model.getObject(parentguid)
            unbounded = parent.find(self.dict['unboundedgeometry'])
        child = unbounded.find('*')  # Retrieve the child surface
        LogMessage(child, self.logging)
        self.surface = child
        return self.surface

    def unboundedGeometryAsSurface(self):
        # UnboundedGeometry
        children = unbounded.findall('*')  # Retrieve all children

        for child in children:
            LogMessage(child, self.logging)
            # if child.tag == self.dict['surface']:
            # edge = self.ellipse(child)

            # elif child.tag == self.dict['cone3d']:
            # edge = self.circumcircle(child)

            # elif child.tag == self.dict['cylinder3d']:
            # edge = self.circle(child)

            if child.tag == self.dict['nurbssurface']:
                mkface = OCXParser.NurbsSurface(child, self.dict)
                if mkface.done:
                    self.face.append(mkface.Value())

            elif child.tag == self.dict['plane3d']:
                mkface = OCXParser.Plane3D(child, self.dict)
                if mkface.done:
                    self.face.append(mkface.Value())

            # elif child.tag == self.dict['surfaceref']:
            # edge = self.compositecurve(child)

            # elif child.tag == self.dict['gridref']:
            # edge = self.polyline(child)

            else:
                print('UnboundedGeometry: Unknown child ', child.tag)
        return self.face


class LogMessage:
    def __init__(self, object, log):
        if log:
            tag = object.tag
            id = object.get('name')
            if id == None:
                id = object.get('id')
            print('Parsing element : {} with id: {}'.format(tag, id))
        return

class Message:
    def __init__(self, object, msg):
        tag = object.tag
        id = object.get('id')
        print('OCX message: in {} with id {}: {} '.format(tag, id, msg))
        return

def find_replace_multi(string, dictionary):
    for item in dictionary.keys():
        # sub item for item's paired value in string
        string = re.sub(item, dictionary[item], string)
    return string