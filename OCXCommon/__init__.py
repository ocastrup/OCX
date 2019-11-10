#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

# Class for UnitsML encapsulation

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