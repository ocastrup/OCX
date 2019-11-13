#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import xml.etree.ElementTree as ET

import numpy
import os, logging
import re
from pathlib import Path
import OCXParser


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

    def getSeams(self):
        return self.root.findall('.//' + self.dict['seam'])

# Class to parse the OCX model
class OCXmodel:
    def __init__(self, ocxfile: str, schemafile: str, log=False):
        self.ocxfile = Path(ocxfile)  # Encapsulate the input file name in a Path object
        self.ocxschema = Path(schemafile)
        self.logging = log
        # Create the schema parser and get the namespaces
        sparser = OCXschema(self.ocxschema)
        self.namespace = sparser.getNameSpace()
        self.schema_version = sparser.version
        self.dict = sparser.dict  # The dictionary of parsable ocx elements
        self.guids = {}  # GUID lookup table
        self.frametable = {}  # Frametable dict with guid as key
        self.logger = logging.getLogger(__name__)

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
            msg = ('Warning: Version {} of the OCX model is different from the referenced schema version: {}' \
                  .format(self.ocxversion, self.schema_version))
            self.logger.warning(msg)
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
        # Stiffeners
        self.seams = self.dom.getSeams()
        # Materials
        self.materials = self.dom.getMaterials()
        # Sections
        self.sections = self.dom.getSections()
        # Pillars
        self.pillars = self.dom.getPillars()
        # Frame lookup table
        self.createFrameTable()
        # Guid lookup table
        self.createGUIDTable()
        # Find all panel children
        self.findPanelChildren()
        #Model info
        self.modelInfo()
        return

    def getPanels(self):
        return self.panels

    def getPlates(self):
        return self.plates

    def getStiffeners(self):
        return self.stiffeners

    def getBrackets(self):
        return self.brackets

    def getMaterials(self):
        return self.materials

    def getSections(self):
        return self.sections

    def getPillars(self):
        return self.pillars

    def getVessel(self):
        return self.vessel

    def getSeams(self):
        return self.seams


    def modelInfo(self):
        nframes = len(self.frametable)
        nplates = len(self.getPlates())
        npanels = len(self.getPanels())
        nstiff = len(self.getStiffeners())
        npil = len(self.getPillars())
        nbr = len(self.getBrackets())
        nseams = len(self.getSeams())
        nmat = len(self.getMaterials())
        nsec = len(self.getSections())
        print('')
        print('Structure parts in model {}'.format(self.ocxfile.name))
        print('-------------------------------------')
        print('Number of vessels         : {:9}'.format(1))
        print('Number of reference grids : {:9}'.format(nframes))
        print('Number of panels          : {:9}'.format(npanels))
        print('Number of plates          : {:9}'.format(nplates))
        print('Number of stiffeners      : {:9}'.format(nstiff))
        print('Number of pillars         : {:9}'.format(npil))
        print('Number of brackets        : {:9}'.format(nbr))
        print('Number of seams           : {:9}'.format(nseams))
        print('Number of materials       : {:9}'.format(nmat))
        print('Number of sections        : {:9}'.format(nsec))
        print('-------------------------------------')
        parts = 1 + nframes + npanels + nplates + nstiff + npil + nbr + nseams + nmat + nsec
        print('Total number of parts     : {:9}'.format(parts))
        print('-------------------------------------')
        print('')
        return

    def totalPlateDryWeight(self)->float:
        dw = 0
        for object in self.getPlates():
            part = StructurePart(self, object,self.dict, self.namespace)
            guid = part.getGuid()
            if self.getParentPanelGuid(guid) == 'NotFound':
                dw = dw + part.getDryWeight()
        return dw

    def totalStiffenerDryWeight(self)->float:
        dw = 0
        for object in self.getStiffeners():
            part = StructurePart(self, object, self.dict, self.namespace)
            guid = part.getGuid()
            if self.getParentPanelGuid(guid) == 'NotFound':
                dw = dw + part.getDryWeight()
        return dw

    def totalBracketDryWeight(self)-> float:
        dw = 0
        for object in self.getBrackets():
            part = StructurePart(self, object, self.dict, self.namespace)
            guid = part.getGuid()
            if self.getParentPanelGuid(guid) == 'NotFound':
                dw = dw + part.getDryWeight()
        return dw

    def totalPanelDryWeight(self)->tuple:
        paneldw = 0
        cdw = 0
        for object in self.getPanels():
            part = StructurePart(self, object, self.dict, self.namespace)
            dw = part.getDryWeight()
            if not dw == None:
                paneldw = paneldw + dw
            children = self.getPanelChildren(part.getGuid())
            for child in children:
                object = self.getObject(child)
                part = StructurePart(self, object, self.dict, self.namespace)
                if part.hasPysicalProperties():
                    dw = part.getDryWeight()
                    if not dw == None:
                        cdw = cdw + dw
        return (paneldw, cdw)

    def printDryWeight(self):
        wpanels = self.totalPanelDryWeight()
        wplates = self.totalPlateDryWeight()
        wstiff = self.totalStiffenerDryWeight()
        wbr = self.totalBracketDryWeight()
        print('')
        print('Dry weight of parts in model {}'.format(self.ocxfile.name))
        print('-------------------------------------')
        print('Panels              : {:12.6e}'.format(wpanels[0]))
        print('  Panel children    : {:12.6e}'.format(wpanels[1]))
        print('Root plates         : {:12.6e}'.format(wplates))
        print('Root stiffeners     : {:12.6e}'.format(wstiff))
        print('Root brackets       : {:12.6e}'.format(wbr))
        print('-------------------------------------')
        if wpanels[0] > 0:
            wp = wpanels[0]
        else:
            wp = wpanels[1]
        total = wp + wplates + wstiff + wbr
        print('Total weight        : {:12.6e}'.format(total))
        print('-------------------------------------')
        print('')
        return

    def modelQA(self):
        # Duplicate GUIDS
        print('QA checks on model {}'.format(self.ocxfile.name))
        print('-------------------------------------')
        self.checkPhysicalProperties()
        self.checkDuplicates()
        self.checkWeights()
        return

    def checkWeights(self): # Check if reported dry weight of Panel is equal to the sum of child weights
        print('Checking Panel dry weights')
        ok = True
        for object in self.getPanels():
            panel = StructurePart(self, object, self.dict, self.namespace)
            if panel.hasPysicalProperties():
                pw = panel.getDryWeight()
                children = self.getPanelChildren(panel.getGuid())
                cw = 0
                for child in children:
                    object = self.getObject(child)
                    part = StructurePart(self, object, self.dict, self.namespace)
                    if part.hasPysicalProperties():
                        cw = cw + part.getDryWeight()
                r = abs(1-cw/pw)
                if r > 0.1:
                    print('Panel with name {} and GUID {}:'.format(panel.getName(),panel.getGuid()))
                    print('  The Panel DryWeight = {:9.3f} is different from the sum of child weights ={:9.3f}.'\
                           .format(pw, cw))
                    ok = False
        if ok:
            print('Panel dry weights OK')
        print('-------------------------------------')
        return

    def checkDuplicates(self):
        if len(self.duplicates) > 0:  # Non-unique quids
            print('Duplicate GUID check')
            msg =('There are {} non unique guids:'.format(len(self.duplicates)))
            print(msg)
            for object in self.duplicates:
                part = StructurePart(self, object, self.dict, self.namespace)
                name = part.getName()
                id = part.getId()
                tag = part.getType()
                guid = part.getGuid()
                msg =('Part {} with name {}, id {}  and GUID {} is a duplicate.'.format(tag, name, id, guid))
                print(msg)
        else:
            print('Duplicate GUID check OK')
        print('-------------------------------------')
        return

    def checkPhysicalProperties(self):
        # Check Existence of properties
        guids = self.getGUIDs()
        nprops = 0
        for guid in guids:
            object = self.getObject(guid)
            part = OCXParser.StructurePart(self, object,self.dict,self.namespace)
            if not part.hasPysicalProperties():
                type = part.getType()
                if type == 'Panel' or type == 'Stiffener' or type == 'Plate' or type == 'Bracket':
                    print('{} with guid {} has no PhysicalProperty'.format(part.getType(), part.getGuid()))
                    nprops = nprops + 1
        if nprops > 0:
            print('PhysicalProperty check:')
            print('Structure parts without PhysicalProperty: {}'.format(nprops))
        else:
            print('PhysicalProperty check OK')
        print('-------------------------------------')
        return

    # Find all children structure parts of  the panels and store it's guids  in a dict with the panel guid as key
    def findPanelChildren(self):
        panels = {}
        for panel in self.getPanels():
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
            # Seams
            seams = []
            children = panel.findall('.//' + self.dict['seam'])
            for child in children:
                childguid = self.getGUID(child)
                seams.append(childguid)
            # Add all children
            panels[panelguid] = plates + stiffeners + brackets + pillars + seams
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
    def objectType(self, guid: str):
        if guid in self.guids:
            object = self.guids[guid]
            return object.tag
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
        #  Only one Vessel
        guid = self.getGUID(self.vessel)
        if not guid in guids:
            guids[guid] = self.vessel
        else:
            duplicates.append(self.vessel)
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
        for part in self.seams:
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
        # Frametables
        for part in self.xrefs:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.yrefs:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        for part in self.zrefs:
            guid = self.getGUID(part)
            if not guid in guids:
                guids[guid] = part
            else:
                duplicates.append(part)
        self.guids = guids
        self.duplicates = duplicates

    def createFrameTable(self):
        frametable = self.root.find('.//' + self.dict['frametables'])
        if not frametable == None:
            tbl = FrameTable(frametable, self.dict, self.namespace, self.logging)
            self.xrefs = tbl.xRef()
            self.yrefs = tbl.yRef()
            self.zrefs = tbl.zRef()
            self.frametable = tbl.frametable

    def printFrameTable(self):
        for frame in self.frametable:
            print('Frame: {}, Position: {}, NormalVector: {}'.format(frame, self.frametable[frame][0],
                                                                     self.frametable[frame][1]))

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
        # Read the table
        self.readTable()
        # Create lookup tabøe
        self.createTable()
        return

    def readTable(self):
        # Get all XRefPlanes
        self.xrefp = self.table.find(self.dict['xrefplanes'])
        self.yrefp = self.table.find(self.dict['yrefplanes'])
        self.zrefp = self.table.find(self.dict['zrefplanes'])


    def xRef(self):
        return self.xrefp

    def yRef(self):
        return self.yrefp

    def zRef(self):
        return self.zrefp

    def createTable(self):
        # X positions
        xrefs = self.xrefp.findall(self.dict['refplane'])
        for ref in xrefs:
            refp = RefPlane(ref, self.dict)
            guid = refp.guid
            refloc = refp.location()
            unit = OCXCommon.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([pos, 0, 0]), numpy.array([1, 0, 0]))  # tuple of ref pos and plane normal vector
        # Y positions
        yrefs = self.yrefp.findall(self.dict['refplane'])
        for ref in yrefs:
            refp = RefPlane(ref, self.dict)
            guid = refp.guid
            refloc = refp.location()
            unit = OCXCommon.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([0, pos, 0]), numpy.array([0, 1, 0]))  # tuple of ref pos and plane normal vector
        # Z positions
        zrefs = self.zrefp.findall(self.dict['refplane'])
        for ref in zrefs:
            refp = RefPlane(ref, self.dict)
            guid = refp.guid
            refloc = refp.location()
            unit = OCXCommon.OCXUnit(self.namespace)
            pos = unit.numericValue(refloc)
            self.frametable[guid] = (
                numpy.array([0, 0, pos]), numpy.array([0, 0, 1]))  # tuple of ref pos and plane normal vector
        return

    def printFrameTable(self):
        for frame in self.frametable:
            print('Frame: {}, Position: {}, NormalVector: {}'.format(frame, self.frametable[frame][0],
                                                                     self.frametable[frame][1]))
class RefPlane:
    def __init__(self, refplane, dict):
        if not refplane == None:
            self.guid = refplane.get(dict['guidref'])
            self.name = refplane.get('name')
            self.refloc = refplane.find(dict['referencelocation'])
            self.ok = True
        else:
            self.guid = None
            self.name = None
            self.refloc = None
            self.ok = False

    def name(self):
        return self.name

    def guid(self):
        return self.guid

    def location(self):
        return self.refloc

class PhysicalProperties:
    def __init__(self, parent, dict, namespace):
        self.hasProp = False
        if not parent == None:
            props = parent.find(dict['physicalproperties'])
            if not props == None:
                dryw = props.find(dict['dryweight'])
                unit = OCXCommon.OCXUnit(namespace)
                self.dryweight = unit.numericValue(dryw)
                cog = props.find(dict['centerofgravity'])
                self.COG = OCXCommon.Point3D(cog, dict).GetPoint()
                self.hasProp = True
        else:
            self.hasProp = False

    def COG(self):
        return self.COG

    def dryWieght(self):
        return self.dryweight

class IDBase:
    def __init__(self, object, dict):
        self.object = object
        self.dict = dict
        self.id = object.get('id')

    def getId(self):
        return self.id

class DescriptionBase(IDBase):
    def __init__(self, object, dict, log=False):
        super().__init__(object, dict)
        self.name = object.get('name')
        if self.name == None:
            self.name = self.id
        description = object.find(dict['description'])
        if description == None:
            self.hasDesc = False
        else:
            self.description = description
            self.hasDesc = True
        return

    def getDescription(self):
        return self.description

    def hasDescription(self):
        return self.hasDesc

    def getName(self):
        return self.name

class EntityBase(DescriptionBase):
    def __init__(self, object, dict):
        super().__init__(object, dict)
        self.guid = self.object.get(self.dict['guidref'])

    def getGuid(self):
        return self.guid

class StructurePart(EntityBase):
    def __init__(self, model, part, dict, namespace):
        super().__init__(part, dict)
        self.namespace = namespace
        self.hasprops = False
        self.model = model
        props = part.find(dict['physicalproperties'])
        if not props == None:
            dryw = props.find(self.dict['dryweight'])
            unit = OCXCommon.OCXUnit(self.namespace)
            self.dryweight = unit.numericValue(dryw)
            cog = props.find(self.dict['centerofgravity'])
            self.COG = OCXCommon.Point3D(cog, dict).GetPoint()
            self.hasprops = True
        else:
            self.hasprops = False

    def getCOG(self):
        return self.COG

    def getDryWeight(self):
        return self.dryweight

    def hasPysicalProperties(self):
        return self.hasprops

    def getType(self):
        tag = str(self.object.tag)
        type = re.sub(r'\{.*\}','', tag) # Returns only the type after the namespace prefix
        return type

    def tightness(self):
        mytype = self.getType()
        if mytype == 'Panel':
            tight = self.object.get('tightness')
        elif mytype == 'Plate': # The plate inherit from Panel
            guid = self.object.getGuid()
            panelguid = self.model.getParentPanelGuid(guid)
            panel = self.model.getObject(panelguid)
            tight = panel.get('tightness')
        else:
            tight = 'Undefined'
        return tight

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
            self.origin = OCXCommon.Point3D(origin, dict).GetPoint()
            self.normal = OCXCommon.Vector3D(normal, dict).GetVector()
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
