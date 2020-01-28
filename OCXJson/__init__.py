#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import json
import uuid
import re
from bidict import bidict

from OCXCommon import StructurePart, LogMessage, Material, ConnectionConfiguration, BarSection
from OCXParser import Panel, OCXmodel, Plate, Bracket, Stiffener


class JSONProperties:
    def __init__(self):
        self.dict = dict([('version', '2')])  # Init  template
        self.attributevalues = {}
        self.properties = {}
        self.attributedefinition = {}
        self.lookuptable = bidict({'lookup': 'table'})
        self.file = 'properties.json'
        self.lookuptable = bidict({'lookup': 'table'})
        self.attributedefinition = {}

    def getPropertyID(self, value):
        return self.lookuptable.inverse[value]

    def getPropertyValue(self, id):
        return self.lookuptable[id]

    def writeJson(self):
        self.dict.update(self.attributevalues)
        self.dict.update(self.properties)
        with open(self.file, 'w') as json_file:
            json.dump(self.dict, json_file, indent=4, sort_keys=False)
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
            # create a bidirectional lookup table for the tuple (valueID,value)
            self.lookuptable[str(guid)] = val
        self.attributevalues['attributeValues'] = attributes
        return

    def addMultipleAttributeValues(self, valuedict):
        attributes = []
        for name in valuedict:
            # json fields
            guid = uuid.uuid1()
            attr = {'valueId': str(guid),
                    'value': name,
                    'metaData': valuedict[name]}
            attributes.append(attr)
            # create a bidirectional lookup table for the tuple (valueID,value)
            self.lookuptable[str(guid)] = name
        self.attributevalues['attributeValues'] = attributes
        return

    def attributeDefinitions(self, aname: str):
        attrib = {}
        attrib['attributeDefinitions'] = \
            [
                {'definitionName': aname,
                 'type': 'string',
                 'enableColorCoding': True,
                 'showAttributeName': True,
                 'colorCodingSettings': None}
            ]
        return attrib


class TrackChanges(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, mappingfile: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if map:
            self.entitymap = EntitiesMap(ocxmodel, mappingfile)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'ModelChange',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        filter = FilterId(ocxmodel, mappingfile)
        self.filterid = filter.filterid
        self.dict.update(self.attributedefinition)

    def baselineChanges(self, deletedparts: dict, modifiedparts: dict, file: str):
        self.file = file
        # Set the property attributes
        values = ['Deleted', 'Modified']
        self.addSingleAttributeValues(values)
        properties = []
        # Find all deleted parts
        id = 0
        for deleted in deletedparts:
            part = StructurePart(deletedparts[deleted], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    id = id + 1
                    propRef = self.getPropertyID('Deleted')
                    property = {'name': 'Model Revisions',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'ModelChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        im = 0
        for mod in modifiedparts:
            part = StructurePart(modifiedparts[mod], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    im = im + 1
                    propRef = self.getPropertyID('Modified')
                    property = {'name': 'Model Revisions',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'ModelChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        self.properties['properties'] = properties
        print('Baseline: Deleted parts: {}'.format(id))
        print('Baseline: Modified or kept parts: {}'.format(im))

    def revisionChanges(self, newparts: dict, modifiedparts: dict, file: str):
        self.file = file
        # Set the property attributes
        values = ['New', 'Modified']
        self.addSingleAttributeValues(values)
        properties = []
        # Find all new parts
        id = 0
        for new in newparts:
            part = StructurePart(newparts[new], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    id = id + 1
                    propRef = self.getPropertyID('New')
                    property = {'name': 'Model Revisions',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'ModelChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        im = 0
        for mod in modifiedparts:
            part = StructurePart(modifiedparts[mod], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    im = im + 1
                    propRef = self.getPropertyID('Modified')
                    property = {'name': 'Model Revisions',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'ModelChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        self.properties['properties'] = properties
        print('Revision: New parts: {}'.format(id))
        print('Revision: Modified or kept parts: {}'.format(im))


class DryWeightChange(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, mappingfile: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if map:
            self.entitymap = EntitiesMap(ocxmodel, mappingfile)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'DryWeightChange',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        filter = FilterId(ocxmodel, mappingfile)
        self.filterid = filter.filterid
        self.dict.update(self.attributedefinition)

    def reportChanges(self, newparts: dict, modifiedparts: dict, weightratio: dict, file: str):
        self.file = file
        # Set the property attributes
        values = ['New', 'Modified']
        for w in weightratio:
            if weightratio[w] not in values:
                values.append(weightratio[w])
        self.addSingleAttributeValues(sorted(values))
        properties = []
        # Find all deleted parts
        id = 0
        for new in newparts:
            id = id + 1
            part = StructurePart(newparts[new], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    propRef = self.getPropertyID('New')
                    property = {'name': 'New',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'DryWeightChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        im = 0
        for mod in modifiedparts:
            part = StructurePart(modifiedparts[mod], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                im = im + 1
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    if gguid in weightratio:
                        propRef = self.getPropertyID(weightratio[gguid])
                    else:
                        propRef = self.getPropertyID('Modified')
                    property = {'name': 'Change',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'DryWeightChange',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        self.properties['properties'] = properties
#        print('New parts: {}'.format(id))
#        print('Modified or kept parts: {}'.format(im))


class PanelChanges(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, mappingfile: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if map:
            self.entitymap = EntitiesMap(ocxmodel, mappingfile)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'Panel Changes',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        filter = FilterId(ocxmodel, mappingfile)
        self.filterid = filter.filterid
        self.dict.update(self.attributedefinition)

    def panelChanges(self, newparts: dict, modifiedparts: dict, weightratio: dict, file: str):
        self.file = file
        # Set the property attributes
        values = ['Modified']
        for w in weightratio:
            if weightratio[w] not in values:
                values.append(weightratio[w])
        self.addSingleAttributeValues(sorted(values))
        properties = []
        # Find all deleted parts
        im = 0
        for mod in modifiedparts:
            part = StructurePart(modifiedparts[mod], self.model.dict)
            type = part.getType()
            if type == 'Plate' or type == 'Stiffener' or type == 'Bracket':
                im = im + 1
                name = part.getName()
                guid = part.getCleanGuid()
                gguid = guid.lower()
                if gguid in self.filterid:
                    if gguid in weightratio:
                        propRef = self.getPropertyID(weightratio[gguid])
                    else:
                        propRef = self.getPropertyID('Modified')
                    property = {'name': 'Modified Panels',
                                'position': None,
                                'entityRef': {
                                    'entityId': gguid,
                                    'description': type + '_' + name
                                },
                                'propertyId': str(uuid.uuid1()),
                                'attributes': [
                                    {
                                        'definitionName': 'Panel Changes',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
        self.properties['properties'] = properties
        print('Modified or kept parts: {}'.format(im))


class TightnessProperty(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'Tightness',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        self.dict.update(self.attributedefinition)

    def tightnessProperty(self, file: str):
        self.file = file
        # Set the property attributes
        enums = self.model.getEnumeration('tightness')
        self.addSingleAttributeValues(enums)
        properties = []
        for part in self.model.getPlates():
            panel = Panel(self.model, part, self.model.dict, self.model.namespace)
            name = panel.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = panel.getGuid()
            name = panel.getName()
            tight = panel.tightness()
            propRef = self.getPropertyID(tight)
            property = {'name': 'Tightness',
                        'position': None,
                        'entityRef': {
                            'entityId': guid,
                            'description': name
                        },
                        'propertyId': str(uuid.uuid1()),
                        'attributes': [
                            {
                                'definitionName': 'Tightness',
                                'valueId': propRef
                            }
                        ]
                        }
            properties.append(property)
        self.properties['properties'] = properties


class FilterId:
    def __init__(self, ocxmodel: OCXmodel, entityfile):
        self.model = ocxmodel
        self.logging = ocxmodel.logging
        self.entities = []
        self.filterid = self.findIds(entityfile)

    def filter(self):
        filterid = []
        for ent in self.entities['roots']:
            if 'children' in ent:
                for child in ent['children']:
                    entityid = child['entityId']
                    filterid.append(entityid)
        print('')
        print('Number of parts filtered: {}'.format(len(filterid)))
        self.filterid = filterid

    def findIds(self, entityfile):
        filter = []
        pattern = 'entityId'
        n = 0
        with open(entityfile, mode='r') as fd:
            for line in fd:
                if re.search(pattern, line):
                    id = line.split(':')
                    entityid = id[1].replace('"', '')
                    entityid = entityid.replace('\n', '')
                    entityid = entityid.replace(' ', '')
                    filter.append(entityid)
                    n = n + 1
        fd.close()
#        print('Number of ids: ', n)
        return filter


class EntitiesMap:
    def __init__(self, ocxmodel: OCXmodel, entityfile):
        self.model = ocxmodel
        self.logging = ocxmodel.logging
        self.json = dict([('modelName', ocxmodel.ocxfile.name)])  # Init  template
        self.root = {}
        self.entities = {}
        self.partmap = {}
        self.filterid = []
        with open(entityfile) as json_file:
            self.entities = json.load(json_file)
        self.createIdentityMap()

    def createIdentityMap(self):
        filterid = []
        i = 0
        names = []
        for ent in self.entities['roots']:
            name = ent['name']
            if name in names:
                i = i + 1
                name = name + '_' + str(i)
            entityid = ent['entityId']
            filterid.append(entityid)
            self.partmap[name] = entityid
            names.append(name)
            if 'children' in ent:
                for child in ent['children']:
                    name = child['name']
                    if name in names:
                        i = i + 1
                        name = name + '_' + str(i)
                    entityid = child['entityId']
                    self.partmap[name] = entityid
                    filterid.append(entityid)
                    names.append(name)
        print('')
        print('Number of parts mapped: {}'.format(len(self.partmap)))
        self.filterid = filterid


    def getFilterId(self):
        return self.filterid

    def getEntityId(self, name: str):  # Return the external entity id (GUID) from the part name
        if name in self.partmap:
            return self.partmap[name]
        else:
            return None

    def printEntityMap(self):
        for name in self.partmap:
            print('Name {} with entityID {}'.format(name, self.partmap[name]))

    def createMap(self):
        # Loop over all Panels
        roots = []
        names = []
        index = 0
        ncount = 0
        panelchildren = []
        for part in self.model.getPanels():
            LogMessage(part, self.logging)
            panel = StructurePart(part, self.model.dict)
            guid = panel.getGuid()
            children = self.model.getPanelChildren(guid)
            # Collect all panel children guids so we later can exclude them from the  root parts
            panelchildren = panelchildren + children
            panelname = panel.getName()
            if panelname in names:
                ncount = ncount + 1
                panelname = panelname + '_' + str(ncount)
                names.append(panelname)
            else:
                names.append(panelname)
            mchildren = []
            ncount = 0
            for child in children:
                object = self.model.getObject(child)
                part = StructurePart(object, self.model.dict)
                name = part.getName()
                if name in names:
                    ncount = ncount + 1
                    name = name + '_' + str(ncount)
                    names.append(name)
                else:
                    names.append(name)
                entityid = part.getCleanGuid()
                mchild = {'name': name,
                          'geoPartIndices': [index],
                          'entityId': entityid
                          }
                index = index + 1
                mchildren.append(mchild)
            entityid = panel.getCleanGuid()
            mpanel = {'name': panelname,
                      'children': mchildren,
                      'entityId': entityid
                      }
            roots.append(mpanel)
        # Root brackets
        mchildren = []
        ncount = 0
        for object in self.model.getBrackets():
            br = StructurePart(object, self.model.dict)
            guid = br.getGuid()
            if guid not in panelchildren:
                name = br.getName()
                if name in names:
                    ncount = ncount + 1
                    name = name + '_' + str(ncount)
                    names.append(name)
                else:
                    names.append(name)
                entityid = br.getCleanGuid()
                mchild = {'name': name,
                          'geoPartIndices': [index],
                          'entityId': entityid
                          }
                index = index + 1
                mchildren.append(mchild)
        mparts = {'name': 'Brackets',
                  'children': mchildren
                  }
        roots.append(mparts)
        # Root plates
        mchildren = []
        for object in self.model.getPlates():
            part = StructurePart(object, self.model.dict)
            guid = part.getGuid()
            if guid not in panelchildren:
                name = part.getName()
                if name in names:
                    ncount = ncount + 1
                    name = name + '_' + str(ncount)
                    names.append(name)
                else:
                    names.append(name)
                entityid = part.getCleanGuid()
                mchild = {'name': name,
                          'geoPartIndices': [index],
                          'entityId': entityid
                          }
                index = index + 1
                mchildren.append(mchild)
        mparts = {'name': 'Plates',
                  'children': mchildren
                  }
        roots.append(mparts)
        # Root pillars
        ncount = 0
        mchildren = []
        for object in self.model.getPillars():
            part = StructurePart(object, self.model.dict)
            guid = part.getGuid()
            if guid not in panelchildren:
                name = part.getName()
                if name in names:
                    ncount = ncount + 1
                    name = name + '_' + str(ncount)
                    names.append(name)
                else:
                    names.append(name)
                entityid = part.getCleanGuid()
                mchild = {'name': name,
                          'geoPartIndices': [index],
                          'entityId': entityid
                          }
                index = index + 1
                mchildren.append(mchild)
        mparts = {'name': 'Pillars',
                  'children': mchildren
                  }
        roots.append(mparts)
        # Root stiffeners
        ncount = 0
        mchildren = []
        for object in self.model.getStiffeners():
            part = StructurePart(object, self.model.dict)
            guid = part.getGuid()
            if guid not in panelchildren:
                name = part.getName()
                if name in names:
                    ncount = ncount + 1
                    name = name + '_' + str(ncount)
                    names.append(name)
                else:
                    names.append(name)
                entityid = part.getCleanGuid()
                mchild = {'name': name,
                          'geoPartIndices': [index],
                          'entityId': entityid
                          }
                index = index + 1
                mchildren.append(mchild)
        mparts = {'name': 'Pillars',
                  'children': mchildren
                  }
        roots.append(mparts)
        self.root['roots'] = roots
        return


class FunctionProperty(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'Structure Function',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        self.dict.update(self.attributedefinition)

    def functionType(self,  file: str):

        self.file = file
        # Set the property attributes
        enums = self.model.getEnumeration('functionType')
        pretty = []
        for enum in enums:
#            pretty.append(self.prettyType(enum))
            pretty.append(enum)
        self.addSingleAttributeValues(pretty)
        properties = []
        # Plates
        for part in self.model.getPlates():
            plate = Plate(self.model, part, self.model.dict, self.model.namespace)
            name = plate.getName()
            function = plate.functionType()
            pfunc = self.prettyType(function)
            self.prettyType(function)
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = plate.getGuid()
#            propRef = self.getPropertyID(pfunc)
            propRef = self.getPropertyID(function)
            property = {'name': 'Structure Function',
                        'position': None,
                        'entityRef': {
                            'entityId': guid,
                            'description': name
                        },
                        'propertyId': str(uuid.uuid1()),
                        'attributes': [
                            {
                                'definitionName': 'Structure Function',
                                'valueId': propRef
                            }
                        ]
                        }
            properties.append(property)
        # Brackets
        for part in self.model.getBrackets():
            plate = Bracket(self.model, part, self.model.dict, self.model.namespace)
            name = plate.getName()
            function = plate.functionType()
            pfunc = self.prettyType(function)
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = panel.getGuid()
            propRef = self.getPropertyID(function)
            property = {'name': 'Structure Function',
                        'position': None,
                        'entityRef':
                            {
                                'entityId': guid,
                                'description': name
                            },
                        'propertyId': str(uuid.uuid1()),
                        'attributes':
                            [
                                {
                                    'definitionName': 'Structure Function',
                                    'valueId': propRef
                                }
                            ]
                        }
            properties.append(property)
        self.properties['properties'] = properties

    def prettyType(self, type: str):  # Returns a human readable type
        # The function Type comes in two standard forms:
        # 1. FUNCION (Capitilized root type)
        # 2. FUNCTION: Sub function ( Sub function given after the colon)
        type = type.replace('_', ' ')
        type = type.title()
        type = type.replace(':', '')
        # Remove repeated words
        words = re.split(' ', type)
        main = words[0]
        sub = False
        for word in words[1:]:
            if word == main:
                sub = True
        if sub:
            type = type[len(main) + 1:]
        return type


class MaterialProperties(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.dict.update(self.attributeDefinitions('Material'))
        self.propertyValues()

    def propertyValues(self):
        # Loop over materials
        propertyvalues = {}
        for mat in self.model.getMaterials():
            material = Material(mat, self.model.dict)
            name = material.getName()
            property = material.getProperty()
            values = []
            properties = property.getProperties()
            for key in properties:
                values.append({
                    'key': key,
                    'value': str(properties[key])
                })
            propertyvalues[name] = values
        self.addMultipleAttributeValues(propertyvalues)
        return

    def assignMaterials(self, file: str):
        self.file = file
        # Set the material attributes
        properties = []
        # Plates
        for part in self.model.getPlates():
            plate = Plate(self.model, part, self.model.dict, self.model.namespace)
            platename = plate.getName()
            material = plate.getMaterial()
            matname = material.getName()
            if self.map:
                guid = self.entitymap.getEntityId(platename)  # Use guid from name map
            else:
                guid = plate.getGuid()
            propRef = self.getPropertyID(matname)
            property = {'name': 'Material',
                        'position': None,
                        'entityRef': {
                            'entityId': guid,
                            'description': platename
                        },
                        'propertyId': str(uuid.uuid1()),
                        'attributes': [
                            {
                                'definitionName': 'Material',
                                'valueId': propRef
                            }
                        ]
                        }
            properties.append(property)
        # Brackets
        names = []
        for part in self.model.getBrackets():
            br = Bracket(self.model, part, self.model.dict, self.model.namespace)
            name = br.getName()
            material = br.getMaterial()
            matname = material.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = br.getGuid()
            if not guid == None and name not in names:
                propRef = self.getPropertyID(matname)
                property = {'name': 'Material',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'Material',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
                names.append(name)
        # Stiffeners
        for part in self.model.getStiffeners():
            stf = Stiffener(self.model, part, self.model.dict, self.model.namespace)
            name = stf.getName()
            material = stf.getMaterial()
            matname = material.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = stf.getGuid()
            if not guid == None:
                propRef = self.getPropertyID(matname)
                property = {'name': 'Material',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'Material',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
        # Pillars
        for part in self.model.getPillars():
            pil = Stiffener(self.model, part, self.model.dict, self.model.namespace)
            name = pil.getName()
            material = pil.getMaterial()
            matname = material.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = pil.getGuid()
            if not guid == None:
                propRef = self.getPropertyID(matname)
                property = {'name': 'Material',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'Material',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
        self.properties['properties'] = properties
        return


class BracketProperties(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.dict.update(self.attributeDefinitions('BracketParameters'))
        self.propertyValues()

    def propertyValues(self):
        # Loop over brackets
        valuedict = {}
        propdict = {}
        ib = 0
        for br in self.model.getBrackets():
            bracket = Bracket(self.model, br, self.model.dict, self.model.namespace)
            guid = bracket.getGuid()
            prop = bracket.getBracketParameters()
            id = prop.getPropertiesID()
            values = prop.getProperties()
            propdict[id] = values

        for id in propdict:
            vals = propdict[id]
            properties = []
            for key in vals:
                value = '{:.3f}'.format(vals[key])
                attr={
                    'key': key,
                    'value': value
                }
                properties.append(attr)
            valuedict[id] = properties
        attributes = []
        for id in valuedict:
            # json fields
            ib = ib + 1
            name = 'Type'+ str(ib)
            attr = {'valueId': id,
                    'value': name,
                    'metaData': valuedict[id]}
            attributes.append(attr)
            # create a bidirectional lookup table for the tuple (valueID,value)
            self.lookuptable[id] = name
        self.attributevalues['attributeValues'] = attributes
        return


    def assignBracketParameters(self, file: str):
        self.file = file
        # Set the material attributes
        properties = []
        # Brackets
        names = []
        for part in self.model.getBrackets():
            br = Bracket(self.model, part, self.model.dict, self.model.namespace)
            name = br.getName()
            par = br.getBracketParameters()
            id = par.getPropertiesID()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = br.getGuid()
            if not guid == None and name not in names:
                propRef = id
                property = {'name': 'BracketParameters',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'BracketParameters',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
                names.append(name)
        self.properties['properties'] = properties
        return


class SectionProperties(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.dict.update(self.attributeDefinitions('Section'))
        self.propertyValues()

    def propertyValues(self):
        # Loop over materials
        propertyvalues = {}
        for sec in self.model.getSections():
            section = BarSection(sec, self.model.dict)
            name = section.getName()
            if section.hasBar:
                property = section.getProperty()
                values = []
                properties = property.getProperties()
                for key in properties:
                    values.append({
                        'key': key,
                        'value': str(properties[key])
                    })
                propertyvalues[name] = values
        self.addMultipleAttributeValues(propertyvalues)
        return

    def assignSections(self, file: str):
        self.file = file
        # Set the section attributes
        properties = []
        # Stiffeners
        for part in self.model.getStiffeners():
            stf = Stiffener(self.model, part, self.model.dict, self.model.namespace)
            name = stf.getName()
            section = stf.getSection()
            secname = section.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = stf.getGuid()
            if not guid == None:
                propRef = self.getPropertyID(secname)
                property = {'name': 'Section',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'Section',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
        # Pillars
        for part in self.model.getPillars():
            pil = Stiffener(self.model, part, self.model.dict, self.model.namespace)
            name = pil.getName()
            section = pil.getSection()
            secname = section.getName()
            if self.map:
                guid = self.entitymap.getEntityId(name)  # Use guid from name map
            else:
                guid = pil.getGuid()
            if not guid == None:
                propRef = self.getPropertyID(secname)
                property = {'name': 'Section',
                            'position': None,
                            'entityRef': {
                                'entityId': guid,
                                'description': name
                            },
                            'propertyId': str(uuid.uuid1()),
                            'attributes': [
                                {
                                    'definitionName': 'Section',
                                    'valueId': propRef
                                }
                            ]
                            }
                properties.append(property)
        self.properties['properties'] = properties
        return


class EndConnections(JSONProperties):
    def __init__(self, ocxmodel: OCXmodel, map: bool, entitymap: str):
        super().__init__()
        self.model = ocxmodel
        self.map = map
        if self.map:
            self.entitymap = EntitiesMap(ocxmodel, entitymap)
        self.attributedefinition['attributeDefinitions'] = [{'definitionName': 'EndConnection',
                                                             'type': 'string',
                                                             'enableColorCoding': True,
                                                             'showAttributeName': True,
                                                             'colorCodingSettings': None}]
        self.dict.update(self.attributedefinition)
        # Set the property attributes
        values = ['SingleBracket', 'DoubleBracket', 'WebStiffener', 'WebStiffenerWithSingleBracket',
                  'WebStiffenerWithDoubleBracket', 'Undefined']
        self.addSingleAttributeValues(values)

    def assignConnections(self, file: str):
        self.file = file
        # Set the stiffener connections
        properties = []
        # Stiffeners
        for part in self.model.getStiffeners():
            stf = Stiffener(self.model, part, self.model.dict, self.model.namespace)
            name = stf.getName()
            if stf.hasConnections():
                ic = 0
                connections = stf.getConnectionConfigurations()
                for config in connections:
                    configuration = ConnectionConfiguration(config, self.model.dict)
                    position = configuration.position()
                    type = configuration.connectionType()
                    if self.map:
                        guid = self.entitymap.getEntityId(name)  # Use guid from name map
                    else:
                        guid = stf.getGuid()
                    propRef = self.getPropertyID(type)
                    property = {'name': 'EndConnection',
                                'propertyId': str(uuid.uuid1()),
                                'position':
                                    {
                                        'x': position[0],
                                        'y': position[1],
                                        'z': position[2]
                                    },
                                'attributes': [
                                    {
                                        'definitionName': 'EndConnection',
                                        'valueId': propRef
                                    }
                                ]
                                }
                    properties.append(property)
                    ic = ic + 1
                self.properties['properties'] = properties
        return
