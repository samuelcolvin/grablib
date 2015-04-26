from .process import process_file
from .common import VERSION

import argparse
from . import process_file
from .common import VERSION

parser = argparse.ArgumentParser(description="""GrabLib

Utility for defining then downloading, concatenating and minifying your
projects external library files eg. Javascript, CSS.

GrabLib Version: %s
(https://github.com/samuelcolvin/GrabLib).
All optional arguments can also be set in the definition file.

""" % VERSION, formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-t', '--libs-root', action='store', dest='libs_root',
                    help='Root directory to put downloaded files in, defaults to the working directory.')

parser.add_argument('-s', '--libs-root-slim', action='store', dest='libs_root_slim',
                    help='Root directory to put slimmed files in, defaults to libs_root.')

parser.add_argument('-w', '--overwrite', action='store', dest='overwrite',
                    help='Overwrite existing files, default is not to download a library if the file already exists')

parser.add_argument('-p', '--file-permissions', action='store', dest='file_permissions',
                    help='Explicitly set file permission for each file downloaded, eg. 666')

parser.add_argument('-v', '--verbosity', action='store', choices=['0', '1', '2', '3'], dest='verbosity',
                    help='Verbosity Level 0 (nothing except errors), 1 (a little), 2 (default), 3 (everything)')

parser.add_argument('--no-colour', action='store_false', default=True, dest='colour_print',
                    help='Do not use color term to colourise output')

parser.add_argument('file_path', metavar='file-path', default='grablib.json', nargs='?',
                    help='path to JSON or python file defining files to download')


def parse_cmd_arguments(args_namespace=None, from_command_line=True):
    args_namespace = args_namespace or parser.parse_args()
    options = vars(args_namespace)
    process_file(from_command_line=from_command_line, **options)

