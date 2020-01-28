#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import json
import argparse
import OCXJson
import OCXParser
from OCXCommon import StructurePart
from OCXJson import TightnessProperty, EntitiesMap


def main():
    # Construct the argument parser
    argp = argparse.ArgumentParser(prog='diffOCX',
                                   usage='%(prog)s [options] OCXfile1 OCXfile2 schema',
                                   description="Compare the two OCX models and identify differences.")
    # Add the arguments to the parser
    argp.add_argument("-model", type=str, help="The baseline OCX model.", default='OCX_Models/Submission_V1.xml')
    argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema_V282.xsd')
    argp.add_argument("-m", "--map", default=True, type=bool, help="Map OCX guids to input guids")
    argp.add_argument("-e", "--entitymap", default="OCX_Models/Submission_V1_entities_meta.json", type=str, help="Entity map from Sesam Insight")
    argp.add_argument("-o", "--output", default='ocxdiff.txt', type=str, help="Name of output file for report")
    argp.add_argument("-l", "--log", default=False, type=bool,
                      help="Output logging information. This is useful for debugging")
    argp.add_argument("-log", "--logfile", default=__name__ + '.log', type=str,
                      help="Output logging information. This is useful for debugging")
    argp.add_argument("-level", "--level", default='DEBUG', type=str, help='Log level. DEBUG is most verbose')
    options = argp.parse_args()

    # Set up the logger
    model = OCXParser.OCXmodel(options.model, options.schema, options.log)
    model.importModel()
    json = OCXJson.MaterialProperties(model, options.map, options.entitymap)
    json.assignMaterials('JSON_outputfiles/material_properties.json')
    json.writeJson()
    json = OCXJson.BracketProperties(model, options.map, options.entitymap)
    json.assignBracketParameters('JSON_outputfiles/bracket_properties.json')
    json.writeJson()
#    json = OCXJson.SectionProperties(model, options.map, options.entitymap)
#    json.assignSections('JSON_outputfiles/section_properties.json')
#    json.writeJson()
#    json = OCXJson.TightnessProperty(model, options.map, options.entitymap)
#    json.tightnessProperty('JSON_outputfiles/tightness_properties.json')
#    json.writeJson()
#    json = OCXJson.FunctionProperty(model, options.map, options.entitymap)
#    json.functionType('JSON_outputfiles/function_properties.json')
#    json.writeJson()

#  json.createMap()
#  json.writeJson()

if __name__ == '__main__':
   main()
