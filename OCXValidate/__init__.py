#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import logging
from OCXCommon import Material
from OCXParser import OCXmodel, Panel, Plate
from OCXCommon import StructurePart


class Validator:
    def __init__(self, ocxmodel: OCXmodel):
        self.model = ocxmodel
        self.dict = ocxmodel.dict
        self.namespace = ocxmodel.namespace
        self.logger = logging.getLogger(__name__)


    def checkModel(self):
        print('Performing QA checks on model {}'.format(self.model.getModelName()))
        print('-------------------------------------')
        self.checkPanelElements()
        self.checkPhysicalProperties()
        self.checkDuplicates()
        self.checkWeights()
        self.checkFunctionType()
        self.checkTightness()
        self.checkPartMaterial()
        self.checkMaterial()
        return


    def checkWeights(self): # Check if reported dry weight of Panel is equal to the sum of child weights
            print('Checking Panel dry weights')
            ok = True
            for object in self.model.getPanels():
                panel = Panel(self.model, object, self.dict, self.namespace)
                if panel.hasPysicalProperties():
                    if not panel.isVirtual():
                        pw = panel.getDryWeight()
                        children = self.model.getPanelChildren(panel.getGuid())
                        cw = 0
                        for child in children:
                            object = self.model.getObject(child)
                            part = StructurePart( object, self.dict)
                            if part.hasPysicalProperties():
                                cw = cw + part.getDryWeight()
                        r = abs(1-cw/pw)
                        if r > 0.1:
                            print('Panel with name {} and GUID {}:'.format(panel.getName(),panel.getGuid()))
                            print('  The Panel DryWeight = {:12.3f} is different from the sum of child weights ={:12.3f}.'\
                                   .format(pw, cw))
                            ok = False
            if ok:
                print('Panel dry weights OK')
            print('-------------------------------------')
            return


    def checkDuplicates(self):
        ndupl = len(self.model.getDuplicates())
        if ndupl > 0:  # Non-unique quids
            print('Duplicate GUID check')
            msg =('There are {} non unique guids:'.format(ndupl))
            print(msg)
            for object in self.model.getDuplicates():
                part = StructurePart( object, self.dict)
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

    def checkTightness(self):
        # loop over Panels
        print('Panel tightness check')
        n = 0
        ni = 0
        for part in self.model.getPanels():
            panel = Panel(self.model, part, self.dict, self.namespace)
            guid = panel.getGuid()
            type = panel.getType()
            tightness = part.get(self.dict['tightness'])
            if tightness == None:
                OCXCommon.Message(panel,' has no mandatory tightness')
                n = n + 1
            else:
                values = self.model.getEnumeration('tightness')
                if tightness not in values:
                    msg =  '{} with guid {} has illegal tightness value {}'.format(type, guid, tightness)
                    print(msg)
                    ni = ni +1
        if n > 0:
            msg =('There are {} panel(s) without mandatory tightness attribute.'.format(n))
            print(msg)
        elif ni > 0:
            msg =('There are {} panel(s) with illegal tightness value.'.format(ni))
            print('Legal values are: {}'.format(self.model.getEnumeration('tightness')))
            print(msg)
        else:
            print('Tightness check OK')
        print('-------------------------------------')
        return

    def checkPhysicalProperties(self):
            # Check Existence of properties
            nprops = 0
            for object in self.model.getPlates():
                part = StructurePart(object, self.dict)
                if not part.hasPysicalProperties():
                    self.logger.info('{} with guid {} has no PhysicalProperty'.format(part.getType(), part.getGuid()))
                    nprops = nprops + 1
            for object in self.model.getBrackets():
                part = StructurePart(object, self.dict)
                if not part.hasPysicalProperties():
                    self.logger.info('{} with guid {} has no PhysicalProperty'.format(part.getType(), part.getGuid()))
                    nprops = nprops + 1
            for object in self.model.getStiffeners():
                part = StructurePart(object, self.dict)
                if not part.hasPysicalProperties():
                    self.logger.info('{} with guid {} has no PhysicalProperty'.format(part.getType(), part.getGuid()))
                    nprops = nprops + 1
            if nprops > 0:
                print('PhysicalProperty existance check on Bracket, Plate & Stiffener:')
                print('Structure parts without PhysicalProperty: {}'.format(nprops))
            else:
                print('PhysicalProperty check OK')
            print('-------------------------------------')
            return

    def checkPartMaterial(self):
        print('Materials existence check:')
        # Check Existence of material on plate and brackets
        pm = 0
        pg = 0
        # Loop over plates
        for part in self.model.getPlates():
            plate = Plate(self.model, part, self.dict, self.namespace)
            type = plate.getType()
            guid = plate.getGuid()
            if not plate.hasMaterial():
                msg = '{} with guid {} has no material'.format(type, guid)
                print(msg)
                pm = pm + 1
        # Loop over brackets
        for part in self.model.getBrackets():
            plate = Plate(self.model, part, self.dict, self.namespace)
            type = plate.getType()
            guid = plate.getGuid()
            if not plate.hasMaterial():
                msg = '{} with guid {} has no material'.format(type, guid)
                print(msg)
                pm = pm + 1
        if pm > 0:
            print('Structure parts without Material: {}'.format(pm))
        else:
            print('Materials check OK')
        print('-------------------------------------')
        return

    def checkMaterial(self):
        print('Materials check:')
        # Check Existence of material grade
        pm = 0
        pg = 0
        # Loop over materials
        for mat in self.model.getMaterials():
            material = Material(mat, self.dict, False)
            type = material.getType()
            guid = material.getGuid()
            if not material.hasGrade():
                pm = pm + 1
                msg = '{} with guid {} has no mandatory material grade'.format(type, guid)
                print(msg)
            else:
                grade = material.getGrade()
                values = self.model.getEnumeration('grade')
                if grade not in values:
                    msg =  '{} with guid {} has illegal material grade {}'.format(type, guid, grade)
                    print(msg)
                    pg = pg + 1
            if material.getDensity()== None:
                msg = '{} with guid {} has no mandatory Density'.format(type, guid)
                print(msg)
            if material.getYoungsModulus()== None:
                msg = '{} with guid {} has no mandatory YoungsModulus'.format(type, guid)
                print(msg)
            if material.getPoissonRatio()== None:
                msg = '{} with guid {} has no mandatory PoissonRatio'.format(type, guid)
                print(msg)
            if material.getYieldStress()== None:
                msg = '{} with guid {} has no mandatory YieldStress'.format(type, guid)
                print(msg)
        if pm > 0:
            print('Materials without mandatory grade: {}'.format(pm))
        elif pg > 0:
            msg = ('There are {} materials(s) with illegal material grade.'.format(pg))
            print('Legal values are: {}'.format(self.model.getEnumeration('grade')))
            print(msg)
        else:
            print('Material grade check OK')
        print('-------------------------------------')
        return

    def checkPanelElements(self):
        print('Panel elements check:')
        # Check for empty sub elements. This is not allowed
        pm = 0
        # Loop over Panels
        for part in self.model.getPanels():
            panel = Panel(self.model, part, self.dict, self.namespace)
            type = panel.getType()
            guid = panel.getGuid()
            element = part.find(self.dict['composedof'])
            if not element == None:
                children = element.find('.//*')
                if children == None:
                    msg = '{} with guid {} has ComposedOf with no content'.format(type, guid)
                    print(msg)
                    pm = pm + 1
            element = part.find(self.dict['stiffenedby'])
            if not element == None:
                children = element.find('.//*')
                if children == None:
                    msg = '{} with guid {} has StiffenedBy with no content'.format(type, guid)
                    print(msg)
                    pm = pm + 1
            element = part.find(self.dict['cutby'])
            if not element == None:
                children = element.find('.//*')
                if children == None:
                    msg = '{} with guid {} has CutBy with no content'.format(type, guid)
                    print(msg)
                    pm = pm + 1
            element = part.find(self.dict['splitby'])
            if not element == None:
                children = element.find('.//*')
                if children == None:
                    msg = '{} with guid {} has SplitBy with no content'.format(type, guid)
                    print(msg)
                    pm = pm + 1
        if pm > 0:
            print('Panels with sub-elements without content: {}'.format(pm))
        else:
            print('Panel elements OK')
        print('-------------------------------------')
        return

    def checkFunctionType(self):
        # loop over Panels
        print('Panel functionType check')
        n = 0
        ni = 0
        for part in self.model.getPanels():
            panel = Panel(self.model, part, self.dict, self.namespace)
            guid = panel.getGuid()
            type = panel.getType()
            function = panel.functionType()
            if function  == None:
                msg = Message(panel,' has no mandatory functionType')
                print(msg)
                n = n + 1
            else:
                values = self.model.getEnumeration('functionType')
                if function not in values:
                    msg =  '{} with guid {} has illegal functionType {}'.format(type, guid, function)
                    print(msg)
                    ni = ni +1
        if n > 0:
            msg =('There are {} panel(s) without mandatory functionType.'.format(n))
            print(msg)
        elif ni > 0:
            msg =('There are {} panel(s) with illegal functionType value.'.format(ni))
            print('Legal values are: {}'.format(self.model.getEnumeration('functionType')))
            print(msg)
        else:
            print('functionType check OK')
        print('-------------------------------------')
        return
