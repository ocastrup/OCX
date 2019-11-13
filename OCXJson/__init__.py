#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import json
import uuid
import re
import OCXParser

class jsonTemplate:
    def __init__(self, file: str):
        self.file = file
        self.dict = dict([('version','2')]) # Init  template
        self.attributevalues = {}


    def writeJson(self):
        with open(self.file, 'w') as json_file:
            json.dump(self.attributevalues, json_file, indent = 4, sort_keys=False)
        return


    def addSingleAttributeValues(self, values):
        attributes = []
        for val in values:
            guid = uuid.uuid1()
            attr = {'valueId': str(guid),
                    'value': val,
                    'metaData': None}
            attributes.append(attr)
        self.attributevalues['attributeValues'] = attributes

class tightnessProperties(jsonTemplate):
    def __init__(self, ocxmodel: OCXParser.OCXmodel, file: str):
        super.__init__(file)
        self.model = ocxmodel
        definition = {('definitionName','Tightness'),
                      ('type' , 'string'),
                      ('enableColorCoding',True),
                      ('showAttributeName',True),
                      ('colorCodingSettings', None)}
        self.dict['attributeDefinitions'] = definition
        self.addSingleAttributeValues({'Undefined','NonTight','WaterTight','GasTight'})
        '''{
              "name": "property-Function_Type-bbbb37c9-1bd2-4257-bb08-91c850163c72",
              "position": null,
              "entityRef": {
                "entityId": "bbbb37c9-1bd2-4257-bb08-91c850163c72",
                "description": "Plate_bbbb37c9-1bd2-4257-bb08-91c850163c72"
              },
              "propertyId": "3880ece7-dcee-4984-a0ed-ed32be8aae66",
              "attributes": [
                {
                  "definitionName": "Function Type",
                  "valueId": "65169667-0024-4a09-a608-c62b19053bcf"
                }
              ]
            }'''
        for part in self.model.getPlates():
            plate = OCXParser.StructurePart(self.model, part, self.model.dict, self.model.namespace)
            guid = plate.getGuid()
            guid = re.sub(r'\{','', guid) # Remove the  brackets
            cleanguid = re.sub(r'\}','', guid) # Remove the  brackets
            name = plate.getName()
            tight = plate.tightness()
            entityref = {('propertyId',cleanguid),
                         ('description',name)}







