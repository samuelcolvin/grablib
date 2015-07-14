import os
import sys
import imp
import json
import collections
from requests.packages import urllib3

from .common import GrablibError, cprint, DEFAULT_OPTIONS
from . import download, minify

try:
    urllib3.disable_warnings()
except AttributeError:
    pass

DEFAULT_FILE_PATH = 'grablib.json'


def grab(lib_def=DEFAULT_FILE_PATH, from_command_line=False, **options):
    """
    Process a file or json string defining files to download and what to do with them.

    :param lib_def: relative path to file defining what to download or valid JSON
    :param from_command_line: set to True to format exceptions ready for the command line
    :param options: additional options, these override anything in file_path, eg. from terminal
    :return: boolean, whether or not files have been downloaded
    """
    if not os.path.exists(lib_def) and lib_def == DEFAULT_FILE_PATH:
        # this is what happens if you just call `grablib` in the terminal and grablib.json doesn't exist
        cprint('File: "%s" doesn\'t exist, use "grablib -h" to get help' % DEFAULT_FILE_PATH, file=sys.stderr)
        return False

    kwarg_options = options
    try:
        if options.get('verbosity') is not None:
            try:
                options['verbosity'] = int(options['verbosity'])
            except ValueError:
                msg = 'problem converting verbosity to int, value: "%s" is not an integer' % options['verbosity']
                raise GrablibError(msg)

        if not os.path.exists(lib_def):
            try:
                lib_def = json.loads(lib_def, object_pairs_hook=collections.OrderedDict)
            except ValueError:
                raise GrablibError('File not found or not valid JSON: %s' % lib_def)
            else:
                process_function = process_json
        else:
            path_lower = lib_def.lower()
            if not any([path_lower.endswith(ext) for ext in ('.py', '.json')]):
                raise GrablibError('Libs definition file does not have extension .py or .json: %s' % lib_def)

            if path_lower.endswith('.py'):
                process_function = process_python_path
            else:
                with open(lib_def) as f:
                    lib_def = json.load(f, object_pairs_hook=collections.OrderedDict)
                process_function = process_json

        libs_info, minify_info, file_options = process_function(lib_def)

        # explicitly set the options to use, starting from defaults, updating with file_options then key word options
        options = DEFAULT_OPTIONS.copy()
        options.update({k: v for k, v in file_options.items() if v is not None})
        options.update({k: v for k, v in kwarg_options.items() if v is not None})
        if libs_info:
            if not download.DownloadLibs(libs_info, **options).download():
                return False
        if minify_info:
            if not minify.MinifyLibs(minify_info, **options).minify():
                return False

    except GrablibError as e:
        if from_command_line:
            cprint('===================\nError: %s' % str(e), 'red', attrs=['bold'],
                   file=sys.stderr, colour_print=options.get('colour_print', True))
            return False
        else:
            raise e
    return True


def process_json(data):
    """
    Takes a json object and extracts libs_info and options
    """
    options = {}
    if 'libs' in data or 'minify' in data:
        libs_info = data.get('libs', None)
        minify_info = data.get('minify', None)

        for k, v in data.items():
            if k in DEFAULT_OPTIONS:
                options[k] = v
        # to support old grablib.json files we have to accept the old "libs_root" name for "download_root"
        if 'download_root' not in options and 'libs_root' in data:
            options['download_root'] = data['libs_root']
    else:
        libs_info, minify_info = None, None
        libs_info = data
    return libs_info, minify_info, options


def ordered_dict(d):
    # make sure the order is at least consistent, we can't do better than this
    return collections.OrderedDict(sorted(d.items(), key=lambda kv: kv[0]))


def process_python_path(python_path):
    """
    Takes the path of a python file and extracts libs_info and options
    """
    try:
        imp.load_source('GrabSettings', python_path)
        import GrabSettings
    except Exception as e:
        raise GrablibError('Error importing %s: %s' % (python_path, str(e)))
    options = {}
    for name in DEFAULT_OPTIONS.keys():
        value = getattr(GrabSettings, name, None)
        if value is not None:
            options[name] = value

    libs_info, minify_info = None, None
    if hasattr(GrabSettings, 'libs'):
        libs_info = ordered_dict(GrabSettings.libs)
    if hasattr(GrabSettings, 'minify'):
        minify_info = ordered_dict(GrabSettings.minify)
    return libs_info, minify_info, options
