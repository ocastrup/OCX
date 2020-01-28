#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import argparse
import os, pathlib, logging
from  OCXDiff import DiffAgent
from OCXParser import OCXmodel
from OCXCommon import StructurePart
from OCXJson import TrackChanges


def main():
    # Set up the logger

    # Construct the argument parser
    argp = argparse.ArgumentParser(prog='diffOCX',
                                     usage='%(prog)s [options] OCXfile1 OCXfile2 schema',
                                     description="Compare the two OCX models and identify differences.")
    # Add the arguments to the parser
    argp.add_argument("-baseline", type=str, help="The baseline OCX model.", default='OCX_Models/MidShip_1118.xml')
    argp.add_argument("-new", type=str, help="The updated OCX model.", default='OCX_Models/MidShip_1121_phase3.xml')
    argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema.xsd')
    argp.add_argument("-p", "--print", default="yes", type=str, help="Report all differences to file")
    argp.add_argument("-o", "--output", default='ocxdiff.txt', type=str, help="Name of output file for report")
    argp.add_argument("-l", "--log", default=False, type=bool, help="Output logging information. This is useful for debugging")
    argp.add_argument("-log", "--logfile", default='diffOCX.log', type=str, help="Output logging information. This is useful for debugging")
    argp.add_argument("-level", "--level", default='WARNING', type=str, help='Log level. DEBUG is most verbose')
    argp.add_argument("-m", "--map", default=False, type=bool, help="Map OCX guids to input guids")
    argp.add_argument("-e", "--entitymap", default="midship_2011_entities_meta.json", type=str, help="Entity map from Sesam Insight") # Used to filter guids

    options = argp.parse_args()
    # Verify that the models and schema exist
    ocx1 = pathlib.Path(options.baseline)
    ocx2 = pathlib.Path(options.new)
    schemafile = pathlib.Path(options.schema)
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if str.upper(options.level) == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    elif str.upper(options.level) == 'ERROR':
        logger.setLevel(logging.ERROR)
    elif str.upper(options.level) == 'WARNING':
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)
    logger.info('Starting comparing OCX versions.')
    logger.info('Baseline model: {}'.format(options.baseline))
    logger.info('Revised model : {}'.format(options.new))

    diff = DiffAgent(options.baseline,options.new, options.schema,options.logfile, True)
    diff.dryWeightChange('JSON_outputfiles/dryweightchange_properties.json',options.map, options.entitymap)
    diff.revisedChanges('JSON_outputfiles/revisedmodel_properties.json',options.map, options.entitymap)
    diff.baselineChanges('JSON_outputfiles/baselinemodel_properties.json',options.map, options.entitymap)

'''
    nd = 0
    for object in diff.deletedParts():
        part = StructurePart(diff.deletedpart[object], diff.dict)
        if part.getType() == 'Panel':
            print('Deleted: ',part.getName(),part.getGuid())
            nd = nd +1
    nn = 0
    for object in diff.newParts():
        part = StructurePart(diff.newpart[object], diff.dict)
        if part.getType() == 'Panel':
            print('New: ',part.getName(), part.getGuid())
            nn = nn + 1
    ns = 0
    for object in diff.sameParts():
        part = StructurePart(diff.samepart[object], diff.dict)
        if part.getType() == 'Panel':
            print('Same: ',part.getName(), part.getGuid())
            ns = ns +1
    print('Deleted panels: ', nd)
    print('Same panels: ', ns)
    print('New panels: ', nn)
    
'''

#        print('Object properties test: Type={}, id={}, name={}, Has props: {}, Has description:{}'\
#        .format(panel.getType(),panel.getId(),panel.getName(),panel.hasPysicalProperties(), panel.hasDescription()))
'''
        # create the diff agent
        model = OCXDiff.OCXDiff(options.ocx1, options.ocx2, options.schema, options.output, options.log)
        print('Number of guids in model {}: {}'.format(model.path1.name,len(model.baseline.getGUIDs())))
        print('Number of guids in model {}: {}'.format(model.path2.name, len(model.newversion.getGUIDs())))
        print('')
        print('Number of new parts in model {}: {}'.format(model.path1.name, len(model.newParts())))
        print('Number of deleted parts in model {}: {}'.format(model.path2.name, len(model.deletedParts())))
        print('Number of existing parts in model {}: {}'.format(model.path2.name, len(model.sameParts())))
'''

if __name__ == "__main__":
    main()

