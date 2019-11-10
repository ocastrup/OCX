#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import argparse
import os, pathlib, logging
import OCXDiff



def main():
    # Set up the logger

    # Construct the argument parser
    argp = argparse.ArgumentParser(prog='diffOCX',
                                     usage='%(prog)s [options] OCXfile1 OCXfile2 schema',
                                     description="Compare the two OCX models and identify differences.")
    # Add the arguments to the parser
    argp.add_argument("-ocx1", type=str, help="The original OCX model.", default='OCX_Models/BAM_OCX_Phase2z_20191106.xml')
    argp.add_argument("-ocx2", type=str, help="The updated OCX model.", default='OCX_Models/BAM_OCX_Phase2z_20191106.xml')
    argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema.xsd')
    argp.add_argument("-p", "--print", default="yes", type=str, help="Report all differences to file")
    argp.add_argument("-o", "--output", default='ocxdiff.txt', type=str, help="Name of output file for report")
    argp.add_argument("-l", "--log", default=False, type=bool, help="Output logging information. This is useful for debugging")
    argp.add_argument("-log", "--logfile", default='diffOCX.log', type=str, help="Output logging information. This is useful for debugging")
    argp.add_argument("-level", "--level", default='INFO', type=str, help='Log level. DEBUG is most verbose')

    options = argp.parse_args()
    # Verify that the models and schema exist
    ocx1 = pathlib.Path(options.ocx1)
    ocx2 = pathlib.Path(options.ocx2)
    schemafile = pathlib.Path(options.schema)
    logger = logging.getLogger('ocx')
    if str.upper(options.level) == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    #Import the model only if the models and schema exist
    if not ocx1.is_file() or not ocx2.is_file():
        print('Please specify the correct model file {}, {}'.format(options.ocx1, options.ocx2))
    elif not schemafile.is_file():
        print('Please specify the correct schema location {}'.format(options.schema))
    else:
        # create the diff agent
        model = OCXDiff.OCXDiff(options.ocx1, options.ocx2, options.schema,  options.log)
        model.importModels()

if __name__ == "__main__":
    main()

