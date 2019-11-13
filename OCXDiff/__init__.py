#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

from pathlib import Path
import OCXParser
import logging

class OCXDiff:
    def __init__(self, ocx1: str, ocx2: str, schema: str, outputfile: str, log=False):
        self.path1 = Path(ocx1)
        self.path2 = Path(ocx2)
        self.schema = Path(schema)
        self.out = Path(outputfile)
        self.logger = logging.getLogger(__name__)
        self.importModels()
        self.newparts = self.findNewParts()
        self.deletedparts = self.findDeletedParts()

    def importModels(self) -> True:
        self.baseline = OCXParser.OCXmodel(self.path1, self.schema, False)
        self.newversion = OCXParser.OCXmodel(self.path2, self.schema, False)
        self.baseline.importModel()
        self.guids1 = self.baseline.getGUIDs()
        self.newversion.importModel()
        self.guids2 = self.newversion.getGUIDs()

    def findNewParts(self):
        newparts  =[]
        self.sameparts = []
        for guid in self.guids2:
            if guid not in self.guids1:
                newparts.append(guid)
            else:
                self.sameparts.append(guid)
        return newparts

    def findDeletedParts(self):
        deletedparts = []
        for guid in self.guids1:
            if guid not in self.guids2:
                deletedparts.append(guid)
        return deletedparts

    def sameParts(self):
        return self.sameparts

    def newParts(self):
        return self.newparts


    def deletedParts(self):
        return self.deletedparts


class FingerPrint:
    def __init__(self, ocx: OCXParser.OCXmodel):
        self.ocx = ocx

#    def panelFingerPrint(self):
#        # The Panel fingerprint is an md5 checksum of the Panel children guids
#    return
