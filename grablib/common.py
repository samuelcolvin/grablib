from __future__ import print_function
import os
import sys
import re

try:
    import termcolor
except ImportError:
    termcolor = None


def cprint(string, *args, **kwargs):
    colour_print = kwargs.pop('colour_print', False)
    if termcolor and colour_print:
        return termcolor.cprint(string, *args, **kwargs)
    else:
        print_file = kwargs.get('file', sys.stdout)
        end = kwargs.get('end', '')
        print(string, end, file=print_file)


colour_lookup = {0: ('red',),
                 1: ('yellow',),
                 2: ('cyan',),
                 3: ('green',)}

DEFAULT_VERBOSITY = 2

DEFAULT_OPTIONS = {
    'libs_root': './static/',
    'libs_root_minified': './static/minifed/',
    'verbosity': DEFAULT_VERBOSITY,
    'overwrite': False,
    'file_permissions': None,
    'output': None,
    'sites': None,
    'colour_print': False
}


class GrablibError(Exception):
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
                 libs_root_minified,
                 overwrite=False,
                 verbosity=DEFAULT_VERBOSITY,
                 file_permissions=None,
                 output=None,
                 colour_print=True,
                 sites=None):
        """
        initialize DownloadLibs.
        :param libs_root: string, root folder to put files in
        :param overwrite: bool, whether or not to overwrite files that already exist, default is False
        :param verbosity: int, what to print
        :param file_permissions: int or None, if not None permissions to give downloaded files eg. 0666
        :param output: function or None, if not None alternative function to recieve output statements.
        :param colour_print: whether to use termcolor to print output in colour
        :param sites: not used, included here to simplify argument layout in MinifyLibs
        """
        self.libs_root = libs_root
        self.libs_root_minified = libs_root_minified
        self.overwrite = overwrite
        self.verbosity = verbosity
        self.colour_print = colour_print
        if output:
            self.output = output
        else:
            self.output = self._output
        if overwrite != DEFAULT_OPTIONS['overwrite']:
            self.output('Overwrite set to %r' % overwrite)
        if verbosity != DEFAULT_OPTIONS['verbosity']:
            self.output('Verbosity set to %d' % verbosity)
        self.file_perm = file_permissions

    def _search_paths(self, path_list, regexes):
        """
        Search paths for one or more regex and yield matching file names and the regex they matched.
        :param path_list: list of paths to search
        :param regexes: list (or single string) of regexes to search for
        :yields: tuples (filepath, regex it matched)
        """
        for fn in path_list:
            for regex in regexes:
                if re.match(regex, fn):
                    yield fn, regex
                    break

    @classmethod
    def _generate_path(cls, *path_args):
        """
        Create path from args if the directory does not exist create it.
        :param path_args: chunks of path
        :return: tuple: (if the path already existed, the new path)
        """
        dest = os.path.join(*path_args)
        if os.path.exists(dest):
            return True, dest
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        return False, dest

    def _write(self, dest, content):
        try:
            content = content.encode('utf8')
        except (UnicodeDecodeError, AttributeError):
            pass
        with open(dest, 'wb') as f:
            f.write(content)
        if self.file_perm:
            os.chmod(dest, self.file_perm)

    def _output(self, line, verbosity=DEFAULT_VERBOSITY, colourv=None):
        if verbosity <= self.verbosity:
            cv = (colourv, verbosity)[colourv is None]
            args = colour_lookup.get(cv, ())
            text = '%s%s' % (' ' * cv, line[:500])
            cprint(text, colour_print=self.colour_print, *args)