#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import logging
import OCXCommon
import OCXParser
from OCXParser import OCXmodel
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
        self.checkPhysicalProperties()
        self.checkDuplicates()
        self.checkWeights()
        self.checkTightness()
        return


    def checkWeights(self): # Check if reported dry weight of Panel is equal to the sum of child weights
            print('Checking Panel dry weights')
            ok = True
            for object in self.model.getPanels():
                panel = StructurePart(self, object, self.dict, self.namespace)
                if panel.hasPysicalProperties():
                    pw = panel.getDryWeight()
                    children = self.model.getPanelChildren(panel.getGuid())
                    cw = 0
                    for child in children:
                        object = self.model.getObject(child)
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
        ndupl = len(self.model.getDuplicates())
        if ndupl > 0:  # Non-unique quids
            print('Duplicate GUID check')
            msg =('There are {} non unique guids:'.format(ndupl))
            print(msg)
            for object in self.model.getDuplicates():
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
    def checkTightness(self):
        # loop over Panels
        print('Panel tightness check')
        n = 0
        ni = 0
        for part in self.model.getPanels():
            panel = OCXCommon.StructurePart(self.model, part, self.dict, self.namespace)
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
        return

    def checkPhysicalProperties(self):
            # Check Existence of properties
            guids = self.model.getGUIDs()
            nprops = 0
            for guid in guids:
                object = self.model.getObject(guid)
                part = OCXCommon.StructurePart(self, object, self.dict, self.namespace)
                if not part.hasPysicalProperties():
                    type = part.getType()
                    if type == 'Panel' or type == 'Stiffener' or type == 'Plate' or type == 'Bracket':
                        self.logger.info('{} with guid {} has no PhysicalProperty'.format(part.getType(), part.getGuid()))
                        nprops = nprops + 1
            if nprops > 0:
                print('PhysicalProperty check:')
                print('Structure parts without PhysicalProperty: {}'.format(nprops))
            else:
                print('PhysicalProperty check OK')
            print('-------------------------------------')
            return