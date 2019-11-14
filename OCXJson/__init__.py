#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import json
import uuid
import re
from  bidict import bidict
import OCXParser

class OCX2JSON:
    def __init__(self, file='properties.json'):
        self.file = file
        self.dict = dict([('version','2')]) # Init  template
        self.attributevalues = {}
        self.properties = {}
        self.attributedefinition = {}
        self.lookuptable = bidict({'lookup':'table'})
        self.attributedefinition['attributeDefinitions'] = {'definitionName': 'Tightness',
                      'type': 'string',
                      'enableColorCoding': True,
                      'showAttributeName': True,
                      'colorCodingSettings': None}
        self.dict.update(self.attributedefinition)

    def writeJson(self):
        self.dict.update(self.attributevalues)
        self.dict.update(self.properties)
        with open(self.file, 'w') as json_file:
            json.dump(self.dict, json_file, indent = 4, sort_keys=False)
        return


    def addSingleAttributeValues(self, values):
        attributes = []
        for val in values:
            guid = uuid.uuid1()
            # json fields
            attr = {'valueId': str(guid),
                    'value': val,
                    'metaData': None}
            attributes.append(attr)
            #create a bidirectional lookup table for the tuple (valueID,value)
            self.lookuptable[str(guid)] = val
        self.attributevalues['attributeValues'] = attributes
        return

    def getPropertyID(self, value):
        return self.lookuptable.inverse[value]

    def getPropertyValue(self, id):
        return self.lookuptable[id]

    def tightnessProperty(self, ocxmodel: OCXParser.OCXmodel, file: str):
        self.model = ocxmodel
        self.file = file
        #Set the property attributes
        self.addSingleAttributeValues({'NonTight','WaterTight','GasTight','Undefined'})
        properties = []
        for part in self.model.getPlates():
            plate = OCXParser.StructurePart(self.model, part, self.model.dict, self.model.namespace)
            guid = plate.getGuid()
            cleanguid = re.sub(r'[\{\}]*','', guid) # Remove the  brackets
            name = plate.getName()
            type = plate.getType()
            tight = plate.tightness()
            propRef = self.getPropertyID(tight)
            property = {'name':'Tightness',
                        'position': None,
                        'entityRef':{
                            'entityId':guid,
                            'description':name
                        },
                        'propertyId':str(uuid.uuid1()),
                        'attributes':[
                            {
                                'definitionName':'Tightness',
                                'valueId':propRef
                            }
                        ]
                        }
            properties.append(property)
        self.properties['properties'] = properties





