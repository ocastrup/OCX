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
        self.logging = log
        logger = logging.getLogger('ocx')

    def importModels(self) -> True:
        self.ocx1 = OCXParser.OCXmodel(self.path1.name, self.schema.name, log)
        self.ocx2 = OCXParser.OCXmodel(self.path2.name, self.schema.name, log)
        self.ocx1.importModel()
        self.ocx2.importModel()

class FingerPrint:
    def __init__(self, ocx: OCXParser.OCXmodel):
        self.ocx = ocx

    def panelFingerPrint(self):
        # The Panel fingerprint is an md5 checksum of the Panel children guids

