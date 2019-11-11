#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import xml.etree.ElementTree as ET

import numpy
import os
import re

import OCXGeometry
import OCXParser

from pathlib import Path

from OCC.Core.BRep import BRep_Builder
# from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection


import OCXCommon
from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shape

from OCXCommon import LogMessage


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
        # ocx = self.root.find('ocxXML', namespace)
        # self.header = Header(ocx, self.dict, False)

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

    def getVessel(self):
        return self.root.find('.//' + self.dict['vessel'])

# Class to parse the OCX model
class OCXmodel:
    def __init__(self, ocxfile: str, schemafile: str, log=False):
        self.ocxfile = Path(ocxfile)  # Encapsulate the input file name in a Path object
        self.ocxschema = Path(schemafile)
        self.logging = log
        # Create the schema parser and get the namespaces
        sparser = OCXschema(self.ocxschema.resolve())
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
        self.dom = OCXdom(self.ocxfile.resolve(), self.dict, self.namespace)
        self.ocxversion = self.dom.version

        # print ocx version and get the root
        self.root = self.dom.getRoot()
        # get the ocxXML header info
        header = Header(self.root, self.dict, self.logging)


        print('Parsing OCX model    : ', self.ocxfile.name)
        print('OCX version          : ', self.ocxversion)
        if header.hasHeader():
            print('Model name           : ', header.name)
            print('Model timestamp      :  {}'.format(header.ts))
            print('Author               :  {}'.format(header.author))
            print('Originating system   :  {}'.format(header.system))
        if self.ocxversion != self.schema_version:
            print('')
            print('Warning: Version {} of the OCX model is different from the referenced schema version: {}' \
                  .format(self.ocxversion, self.schema_version))
            print('')

        # dom queries
        # Vessel
        self.vessel = self.dom.getVessel()
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
        # Find all panel children
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

    def vessel(self):
        return self.vessel


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
            # TODO: Add seams?
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
            tbl = FrameTable(frametable, self.dict, self.namespace, self.logging)
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
            unit = OCXCommon.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([pos, 0, 0]), numpy.array([1, 0, 0]))  # tuple of ref pos and plane normal vector
        # Y positions
        yrefs = yrefp.findall(self.dict['refplane'])
        for ref in yrefs:
            guid = ref.get(self.dict['guidref'])
            refloc = ref.find(self.dict['referencelocation'])
            unit = OCXCommon.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([0, pos, 0]), numpy.array([0, 1, 0]))  # tuple of ref pos and plane normal vector
        # Z positions
        zrefs = zrefp.findall(self.dict['refplane'])
        for ref in zrefs:
            guid = ref.get(self.dict['guidref'])
            refloc = ref.find(self.dict['referencelocation'])
            unit = OCXCommon.OCXUnit(self.namespace)
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

class Description:
    def __init__(self, object, dict, log=False):
        description = object.find(dict['description'])
        if not description == None:
            self.description = description
            self.hasDesc = True
        else:
            self.hasDesc = False

    def description(self):
        return self.description

    def hasDescription(self):
        return self.hasDesc

class Vessel:
    def __init__(self, model: OCXmodel, vessel, dict, log=False):
        self.logging = log
        self.mode = model
        self.vessel = vessel
        self.name = vessel.get('name')
        self.guid = vessel.get(dict['guidref'])

    def name(self):
        if self.name == None:
            self.name = self.vessel.get('id')
        return self.name

    def guid(self):
        return self.guid

class Plane3D:
    def __init__(self, plane, dict, model: OCXmodel):
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
            self.origin = OCXGeometry.Point3D(origin, dict).GetPoint()
            self.normal = OCXGeometry.Vector3D(normal, dict).GetVector()
        elif plane.tag == self.dict['gridref']:
            guid = plane.get(self.dict['guidref'])
            refplane = model.getObject(guid)

    def normal(self) -> numpy.array:
        return self.normal

    def origin(self) -> numpy.array:
        return self.origin


# Return the CompositeCurve as edges




class Material:
    def __init__(self, model: OCXmodel, parent, material, dict, log=False):
        self.dict = dict
        self.logging = log
        self.model = model
        self.material = material
        self.parent = parent

    def thickness(self) -> float:
        thickness = self.material.find(self.dict['thickness'])
        if thickness == None:
            # Assign a default thickness
            th = 0.01
            ParseError(self.parent, 'has no thickness')
        else:
            unit = OCXCommon.OCXUnit()
            th = float(unit.numericValue(thickness))
        return th

# TODO: Implement reading of the product structure
class DesignView:
    def __init__(self, model: OCXmodel, parent, view, dict, log=False):
        self.dict = dict
        self.logging = log
        self.model = model
        self.designview = view
        self.parent = parent

    def modelTree(self) -> "void":
        return


# Return the UnboundedGeometry as a surface
class UnboundedGeometry:
    def __init__(self, model: OCXmodel, object, dict, log=False):
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

            #if child.tag == self.dict['nurbssurface']:
            #    mkface = OCXGeometry.NurbsSurface(child, self.dict)
            #    if mkface.done:
            #        self.face.append(mkface.Value())

            if child.tag == self.dict['plane3d']:
                mkface = Plane3D(child, self.dict)
                if mkface.done:
                    self.face.append(mkface.Value())

            # elif child.tag == self.dict['surfaceref']:
            # edge = self.compositecurve(child)

            # elif child.tag == self.dict['gridref']:
            # edge = self.polyline(child)

            else:
                print('UnboundedGeometry: Unknown child ', child.tag)
        return self.face

def find_replace_multi(string, dictionary):
    for item in dictionary.keys():
        # sub item for item's paired value in string
        string = re.sub(item, dictionary[item], string)
    return string
