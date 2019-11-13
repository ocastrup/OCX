#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

# Class for UnitsML encapsulation
import numpy

import OCXCommon


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
        unit = OCXCommon.OCXUnit(dict)
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