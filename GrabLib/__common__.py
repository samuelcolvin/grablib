import os, re
try:
    from termcolor import cprint
except:
    def cprint(string, *args, **kw):
        if 'end' in kw:
            print(string, kw['end'])
        else:
            print(string)
            
colour_lookup = {0: ('red',),
                 1: ('yellow',),
                 2: ('cyan',),
                 3: ('green',)}

DEFAULT_VERBOSITY = 2
DEFAULTS = {
    'libs_root': '.', 
    'verbosity': DEFAULT_VERBOSITY,
    'overwrite': False,
    'file_permissions': None,
    'output': None,
    'sites': None,
    'libs_root_slim': None,
    'slim': None
}

class KnownError(Exception):
    """
    Exception used when the error is clear so no traceback is required.
    """
    pass

class ProcessBase(object):
    """
    main class for downloading library files based on json file.
    """
    def __init__(self,
                 libs_root, 
                 overwrite=False, 
                 verbosity = DEFAULT_VERBOSITY, 
                 file_permissions = None, 
                 output = None):
        """
        initialize DownloadLibs.
        Args:
            libs_root: string, root folder to put files in
            
            overwrite: bool, whether or not to overwrite files that already exist, default is not to download existing
            
            verbosity: int, what to print 0 (nothing except errors), 1 (less), 2 (default), 3 (everything)
            
            file_permissions: int or None, if not None permissions to give downloaded files eg. 0666
            
            output: function or None, if not None alternative function to recieve output statements.
        """
        self.libs_root = libs_root
        self.overwrite = overwrite
        self.verbosity = verbosity
        if output:
            self.output = output
        else:
            self.output = self._output
        if overwrite != DEFAULTS['overwrite']:
            self.output('Overwrite set to %r' % overwrite)
        if verbosity != DEFAULTS['verbosity']:
            self.output('Verbosity set to %d' % verbosity)
        self.file_perm = file_permissions

    def _generate_path(self, *path_args):
        dest = os.path.join(*path_args)
        if os.path.exists(dest):
            return True, dest
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        return False, dest
    
    def _write(self, dest, content):
        open(dest, 'wb').write(content)
        if self.file_perm:
            os.chmod(dest, self.file_perm)

    def _output(self, line, verbosity = DEFAULT_VERBOSITY, colourv = None):
        if verbosity <= self.verbosity:
            cv = (colourv, verbosity)[colourv is None]
            args = colour_lookup.get(cv, ())
            text = '%s%s' % (' ' * cv, line[:500])
            cprint(text, *args)
