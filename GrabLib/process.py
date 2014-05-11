import os, sys, traceback, imp, json, collections
from .__common__ import KnownError, cprint, DEFAULTS
from . import download, slim

def process_file(file_path, overwrite_options):
    try:
        if overwrite_options['verbosity'] is not None:
            try:
                overwrite_options['verbosity'] = int(overwrite_options['verbosity'])
            except Exception:
                raise KnownError('problem converting verbosity to int, value: "%s" is not an integer'\
                                          % overwrite_options['verbosity'])
        
        if not os.path.exists(file_path):
            raise KnownError('Libs definition file not found: %s' % file_path)
        
        path_lower = file_path.lower()
        if not any([path_lower.endswith(ext) for ext in ('.py', '.json')]):
            raise KnownError('Libs definition file does not have extension .py or .json: %s' % file_path)
        
        dfunc = (process_json_path, process_python_path)[path_lower.endswith('.py')]
        libs_info, slim_info, options = dfunc(file_path)
        options = overwrite_options_update(options, overwrite_options)
        
        if libs_info:
            if not download.DownloadLibs(libs_info, **options).download():
                return False
        if slim_info:
            if not slim.SlimLibs(slim_info, **options).slim():
                return False
        return True
        
    except KnownError as e:
        cprint('===================\nError: %s' % str(e), 'red', attrs=['bold'], file=sys.stderr)
    except Exception as e:
        cprint('Error: %s' % str(e), 'red', attrs=['bold'], file=sys.stderr)
        traceback.print_exc()
    return False

def process_json_path(json_path):
    """
    Takes the path of a json file and extracts libs_info and options
    """ 
    f = open(json_path, 'r')
    try:
        jcontent = json.load(f, object_pairs_hook=collections.OrderedDict)
    except Exception as e:
        raise KnownError('Error Processing JSON: %s' % str(e))
    f.close()
    options = {k:v for k,v in list(DEFAULTS.items())}
    libs_info, slim_info = None, None
    if 'libs' in jcontent or 'slim' in jcontent:
        if 'libs' in jcontent:
            libs_info = jcontent['libs']
        if 'slim' in jcontent:
            slim_info = jcontent['slim']
        for k, v in list(jcontent.items()):
            if k in DEFAULTS:
                options[k] = v
    else:
        libs_info = jcontent
    return libs_info, slim_info, options

def process_python_path(python_fpath):
    """
    Takes the path of a python file and extracts libs_info and options
    """ 
    try:
        imp.load_source('GrabSettings', python_fpath)
        import GrabSettings
    except Exception as e:
        raise KnownError('Error importing %s: %s' % (python_fpath, str(e)))
    options = {k:v for k,v in list(DEFAULTS.items())}
    for name in list(DEFAULTS.keys()):
        if hasattr(GrabSettings, name):
            options[name] = getattr(GrabSettings, name)
    libs_info, slim_info = None, None
    if hasattr(GrabSettings, 'libs'):
        libs_info = collections.OrderedDict(GrabSettings.libs)
    if hasattr(GrabSettings, 'slim'):
        slim_info = collections.OrderedDict(GrabSettings.slim)
    return libs_info, slim_info, options
    
    
def overwrite_options_update(options, overwrite_options):
    """
    Overwrite options (from settings file) with overwrite_options (typically from command line)
    """
    for attr in list(options.keys()):
        if overwrite_options[attr] is not None:
            options[attr] = overwrite_options[attr]
            
    if options['libs_root'] is None:
        raise KnownError('libs_root argument was None and libs_root not defined in definition file')
    
    if options['libs_root_slim'] is None:
        options['libs_root_slim'] = options['libs_root']
    return options