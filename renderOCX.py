#  #!/usr/bin/env python3
#  GNU All-Permissive License
#  Copying and distribution of this file, with or without modification,
#  are permitted in any medium without royalty provided the copyright
#  notice and this notice are preserved.  This file is offered as-is,
#  without any warranty.

import argparse
import os, pathlib
import OCXParser
import OCXGeometry
from OCC.Display.WebGl import x3dom_renderer
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.Interface import Interface_Static_SetCVal
from OCC.Core.IFSelect import IFSelect_RetDone



def main():
    # Construct the argument parser
    argp = argparse.ArgumentParser(prog='renderOCX',
                                     usage='%(prog)s [options] OCXfile schema',
                                     description="Renders the whole OCX model or a part identified by the guid.")
    # Add the arguments to the parser
    argp.add_argument("-file", type=str, help="Your input OCX file.", default='OCX_Models/OpenHCMBox_20191031.xml')
    argp.add_argument("-schema", type=str, help="URI to OCX schema xsd", default='OCX_Models/OCX_Schema.xsd')
    argp.add_argument("-e", "--external", default=True, type=bool, help="Render the model from the external geometry. This is the default")
    argp.add_argument("-s", "--solid", default=False, type=bool, help="Render a solid model. The default is to render a sheet model. This option is only used if option -external=no")
    argp.add_argument("-l", "--log", default=True, type=bool, help="Output logging information. This is useful for debugging")
#    argp.add_argument("-g", "--guid", default='{0010A20F-0000-0000-453F-D518A55C2204}',type=str, help="The GUIDRef of the shape to be rendered. If empty, the whole model is rendered")
    argp.add_argument("-g", "--guid", default='none',type=str, help="The GUIDRef of the shape to be rendered. If empty, the whole model is rendered")
    argp.add_argument("-r", "--render", default=False,type=bool, help="If True, render the model")
    argp.add_argument("-st", "--step", default=True, type=bool, help="Export the OCX model to STEP")
    argp.add_argument("-sf", "--stepfile", default='OCXmodel.stp', type=str, help="File name of STEP export")
    options = argp.parse_args()
    guid = options.guid
    ext = options.external
    # Verify that the model and schema exist
    # create the model parser
    model = OCXParser.OCXmodel(options.file, options.schema, options.log)
    file = pathlib.Path(options.file)
    schemafile = pathlib.Path(options.schema)
    #Import the model only if the model and schema exist
    if not file.is_file():
        print('Please specify the correct model file {}'.format(options.file))
    elif not schemafile.is_file():
        print('Please specify the correct schema location {}'.format(options.schema))
    else:
        model.importModel()
        # Create the geometry creator
        geom = OCXGeometry.OCXGeometry(model, model.dict, options.log)
        # Render only one part
        if not guid =='none':
            if ext == True:
                shapes = geom.externalPartGeometry(guid)
            else:
                shapes = geom.createPartGeometry(guid, options.solid)
        else:
            if ext == True:
                shapes = geom.externalGeometryAssembly()
            else:
                shapes = geom.createGeometry(options.solid)
        if options.step:
            # Export STEP file
            # initialize the STEP exporter
            step_writer = STEPControl_Writer()
            Interface_Static_SetCVal("write.step.schema", "AP203")
            # transfer shapes and write file
            if isinstance(shapes, list):
                for shape in shapes:
                    step_writer.Transfer(shape, STEPControl_AsIs)
            elif not shapes == None:
                 step_writer.Transfer(shapes, STEPControl_AsIs)
            else:
                print('No shapes to export')
            status = step_writer.Write(options.stepfile)
            if status != IFSelect_RetDone:
                raise AssertionError("load failed")
        if options.render:
            #Render shapes
            my_renderer = x3dom_renderer.X3DomRenderer()
            if isinstance(shapes, list):
                for shape in shapes:
                    my_renderer.DisplayShape(shape, export_edges=False)
            elif not shapes == None:
                my_renderer.DisplayShape(shapes, export_edges=False)
            else:
                print('No shapes to render')
            my_renderer.render()

if __name__ == "__main__":
    main()

