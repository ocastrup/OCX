#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import argparse
import os,  logging
from pathlib import Path
import OCXValidate
from OCXCommon import Material, BarSection, ConnectionConfiguration, Property
from OCXParser import Panel, OCXmodel, Plate, Stiffener, Bracket


def main():
    # Set up the logger

    # Construct the argument parser
    argp = argparse.ArgumentParser(prog='diffOCX',
                                     usage='%(prog)s [options] OCXfile1 OCXfile2 schema',
                                     description="Compare the two OCX models and identify differences.")
    # Add the arguments to the parser
    argp.add_argument("-model", type=str, help="The  OCX model.", default='OCX_Models/Submission_V1.xml')
    argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema.xsd')
    argp.add_argument("-p", "--print", default="yes", type=str, help="Report all differences to file")
    argp.add_argument("-o", "--output", default='ocxdiff.txt', type=str, help="Name of output file for report")
    argp.add_argument("-l", "--log", default=False, type=bool, help="Output logging information. This is useful for debugging")
    argp.add_argument("-log", "--logfile", default='diffOCX.log', type=str, help="Output logging information. This is useful for debugging")
    argp.add_argument("-level", "--level", default='WARNING', type=str, help='Log level. DEBUG is most verbose')

    options = argp.parse_args()
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
    logger.info('Starting checking OCX model {}'.format(options.model))
    #The model to parse
    model = OCXmodel(options.model, options.schema, options.log)
    model.importModel()
    model.printDryWeight()


    # Create the model validator
    validate = OCXValidate.Validator(model)
    validate.checkModel()


#        print('Object properties test: Type={}, id={}, name={}, Has props: {}, Has description:{}'\
#        .format(panel.getType(),panel.getId(),panel.getName(),panel.hasPysicalProperties(), panel.hasDescription()))

        # create the diff agent
        # model = OCXDiff.OCXDiff(options.ocx1, options.ocx2, options.schema, options.output, options.log)
        # print('Number of guids in model {}: {}'.format(model.path1.name,len(model.baseline.getGUIDs())))
        # print('Number of guids in model {}: {}'.format(model.path2.name, len(model.newversion.getGUIDs())))
        # print('')
        # print('Number of new parts in model {}: {}'.format(model.path1.name, len(model.newParts())))
        # print('Number of deleted parts in model {}: {}'.format(model.path2.name, len(model.deletedParts())))
        # print('Number of existing parts in model {}: {}'.format(model.path2.name, len(model.sameParts())))


if __name__ == "__main__":
    main()

