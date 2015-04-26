import os
import sys
import imp
import json
import collections

from .common import GrabLibError, cprint, DEFAULT_OPTIONS
from . import download, slim


def process_file(file_path='grablib.json', from_command_line=False, **options):
    """
    Process a file defining files to download and what to do with them.

    :param file_path: relative path to file defining what to download
    :param from_command_line: set to True to format exceptions ready for the command line
    :param options: additional options, these override anything in file_path, eg. from terminal
    :return: boolean, whether or not files have been downloaded
    """
    kwarg_options = options
    try:
        if options.get('verbosity') is not None:
            try:
                options['verbosity'] = int(options['verbosity'])
            except ValueError:
                msg = 'problem converting verbosity to int, value: "%s" is not an integer' % options['verbosity']
                raise GrabLibError(msg)

        if not os.path.exists(file_path):
            raise GrabLibError('File not found: %s' % file_path)

        path_lower = file_path.lower()
        if not any([path_lower.endswith(ext) for ext in ('.py', '.json')]):
            raise GrabLibError('Libs definition file does not have extension .py or .json: %s' % file_path)

        dfunc = process_python_path if path_lower.endswith('.py') else process_json_path
        libs_info, slim_info, file_options = dfunc(file_path)

        # explicitly set the options to use, starting from defaults, updating with file_options then key word options
        options = DEFAULT_OPTIONS.copy()
        options.update({k: v for k, v in file_options.items() if v is not None})
        options.update({k: v for k, v in kwarg_options.items() if v is not None})
        if libs_info:
            if not download.DownloadLibs(libs_info, **options).download():
                return False
        if slim_info:
            if not slim.SlimLibs(slim_info, **options).slim():
                return False

    except GrabLibError as e:
        if from_command_line:
            cprint('===================\nError: %s' % str(e), 'red', attrs=['bold'],
                   file=sys.stderr, colour_print=options.get('colour_print', True))
            return False
        else:
            raise e
    return True


def process_json_path(json_path):
    """
    Takes the path of a json file and extracts libs_info and options
    """
    f = open(json_path, 'r')
    try:
        content = json.load(f, object_pairs_hook=collections.OrderedDict)
    except Exception as e:
        raise GrabLibError('Error Processing JSON: %s' % str(e))
    f.close()
    options = {}
    libs_info, slim_info = None, None
    if 'libs' in content or 'slim' in content:
        if 'libs' in content:
            libs_info = content['libs']
        if 'slim' in content:
            slim_info = content['slim']
        for k, v in list(content.items()):
            if k in DEFAULT_OPTIONS:
                options[k] = v
    else:
        libs_info = content
    return libs_info, slim_info, options


def ordered_dict(dict):
    # make sure the order is at least consistent, we can't do better than this
    return collections.OrderedDict(sorted(dict.items(), key=lambda d: d[0]))


def process_python_path(python_path):
    """
    Takes the path of a python file and extracts libs_info and options
    """
    try:
        imp.load_source('GrabSettings', python_path)
        import GrabSettings
    except Exception as e:
        raise GrabLibError('Error importing %s: %s' % (python_path, str(e)))
    options = {}
    for name in DEFAULT_OPTIONS.keys():
        value = getattr(GrabSettings, name, None)
        if value is not None:
            options[name] = value

    libs_info, slim_info = None, None
    if hasattr(GrabSettings, 'libs'):
        libs_info = ordered_dict(GrabSettings.libs)
    if hasattr(GrabSettings, 'slim'):
        slim_info = ordered_dict(GrabSettings.slim)
    return libs_info, slim_info, options
