from __future__ import print_function, unicode_literals

import os
import re
import logging

logger = logging.getLogger('grablib')


try:
    basestring = basestring
except NameError:
    # py3
    basestring = str


colour_lookup = {0: ('red',),
                 1: ('yellow',),
                 2: ('cyan',),
                 3: ('green',)}

DEFAULT_VERBOSITY = 2

DEFAULT_OPTIONS = {
    'download_root': './static/',
    'minified_root': './static/minifed/',
    'verbosity': DEFAULT_VERBOSITY,
    'overwrite': False,
    'file_permissions': None,
    'sites': None,
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
                 download_root,
                 minified_root=None,
                 overwrite=False,
                 verbosity=DEFAULT_VERBOSITY,
                 file_permissions=None,
                 sites=None):
        """
        initialize DownloadLibs.
        :param download_root: string, root folder to put files in
        :param minified_root: string, root folder for minified and concatenated files
        :param overwrite: bool, whether or not to overwrite files that already exist, default is False
        :param verbosity: int, what to print
        :param file_permissions: int or None, if not None permissions to give downloaded files eg. 0666
        :param sites: not used, included here to simplify argument layout in MinifyLibs
        """
        self.download_root = download_root
        self.minified_root = minified_root
        self.overwrite = overwrite
        self.verbosity = verbosity
        if overwrite != DEFAULT_OPTIONS['overwrite']:
            logger.info('Overwrite set to %r' % overwrite)
        self.file_perm = file_permissions

    def _search_paths(self, path_list, regexes):
        """
        Search paths for one or more regex and yield matching file names and the regex they matched.
        The order of the returned files will match the order of regexes if possible.
        :param path_list: list of paths to search
        :param regexes: list (or single string) of regexes to search for
        :yields: tuples (filepath, regex it matched)
        """
        if isinstance(regexes, basestring):
            regexes = [regexes]
        for regex in regexes:
            for fn in path_list:
                if re.match(regex, fn):
                    yield fn, regex

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
