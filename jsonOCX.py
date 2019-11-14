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



def main():
  # Construct the argument parser
  argp = argparse.ArgumentParser(prog='diffOCX',
                                 usage='%(prog)s [options] OCXfile1 OCXfile2 schema',
                                 description="Compare the two OCX models and identify differences.")
  # Add the arguments to the parser
  argp.add_argument("-baseline", type=str, help="The baseline OCX model.", default='OCX_Models/MidShip_1111.ocx')
  argp.add_argument("-new", type=str, help="The updated OCX model.", default='OCX_Models/MidShip_1111.ocx')
  argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema.xsd')
  argp.add_argument("-p", "--print", default="yes", type=str, help="Report all differences to file")
  argp.add_argument("-o", "--output", default='ocxdiff.txt', type=str, help="Name of output file for report")
  argp.add_argument("-l", "--log", default=False, type=bool,
                    help="Output logging information. This is useful for debugging")
  argp.add_argument("-log", "--logfile", default='diffOCX.log', type=str,
                    help="Output logging information. This is useful for debugging")
  argp.add_argument("-level", "--level", default='DEBUG', type=str, help='Log level. DEBUG is most verbose')
  options = argp.parse_args()

  # Set up the logger
  json = OCXJson.OCX2JSON()
  model = OCXParser.OCXmodel(options.baseline, options.schema, options.log)
  model.importModel()
  json.tightnessProperty(model, 'properties.json')
  json.writeJson()

if __name__ == '__main__':
   main()
