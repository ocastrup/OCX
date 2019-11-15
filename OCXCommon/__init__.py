#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

# Class for UnitsML encapsulation
import re
import logging
import numpy

from OCXParser import OCXmodel


class OCXUnit: #TODO: Implement parsing of UnitsML types
    def __init__(self, namespace=None):
        self.namespace = namespace


#Retrive the quantity numeric value
    def numericValue(self, quantity): #TODO: Implement unit conversion
        value = quantity.get('numericvalue')
        unit = quantity.get('unit')
        return float(value) # Convert string to float

# Common messaging
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


class Point3D:
    def __init__(self, point, dict):
        # Function to retrieve the coordinates from an 'Point3D' type
        # RETURNS:   the (x,y,z) coordinate
        x = point.find(dict['x'])
        y = point.find(dict['y'])
        z = point.find(dict['z'])
        unit = OCXUnit(dict)
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
                unit = OCXUnit(namespace)
                self.dryweight = unit.numericValue(dryw)
                cog = props.find(dict['centerofgravity'])
                self.COG = Point3D(cog, dict).GetPoint()
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

    def getCleanGuid(self):
        cleanguid = re.sub(r'[\{\}]*', '', self.guid)  # Remove the  brackets
        return cleanguid

class StructurePart(EntityBase):
    def __init__(self, model: OCXmodel, part, dict, namespace):
        super().__init__(part, dict)
        self.namespace = namespace
        self.hasprops = False
        self.model = model
        props = part.find(dict['physicalproperties'])
        if not props == None:
            dryw = props.find(self.dict['dryweight'])
            unit = OCXUnit(self.namespace)
            self.dryweight = unit.numericValue(dryw)
            cog = props.find(self.dict['centerofgravity'])
            self.COG = Point3D(cog, dict).GetPoint()
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
            guid = self.getGuid()
            panelguid = self.model.getParentPanelGuid(guid)
            if panelguid == 'NotFound':
                tight = 'Undefined'
            else:
                panel = self.model.getObject(panelguid)
                tight = panel.get(self.dict['tightness'])
                if tight == None:
                    tight = 'Undefined'
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


class Vessel(EntityBase):
    def __init__(self, model: OCXParser.OCXmodel, vessel, dict, log=False):
        super().__init__(vessel, dict)
        self.logging = log
        self.model = model


class Plane3D:
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
            self.origin = OCXCommon.Point3D(origin, dict).GetPoint()
            self.normal = OCXCommon.Vector3D(normal, dict).GetVector()
        elif plane.tag == self.dict['gridref']:
            guid = plane.get(self.dict['guidref'])
            refplane = model.getObject(guid)

    def normal(self) -> numpy.array:
        return self.normal

    def origin(self) -> numpy.array:
        return self.origin


class Material(DescriptionBase):
    def __init__(self, parent, material, dict, log=False):
        super().__init__(material, dict)
        self.logging = log
        self.parent = parent

    def thickness(self) -> float:
        thickness = self.object.find(self.dict['thickness'])
        if thickness == None:
            # Assign a default thickness
            th = 0.01
            Message(self.parent, 'has no thickness')
        else:
            unit = OCXUnit()
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

        return