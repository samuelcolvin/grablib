from __future__ import unicode_literals

import os
import logging

import click

logger = logging.getLogger('grablib')

try:
    str = basestring
except NameError:
    # py3
    str = str

DEFAULT_OPTIONS = {
    'download_root': './static/',
    'minified_root': './static/minifed/',
    'overwrite': False,
    'file_permissions': None,
    'sites': None,
}


class ClickHandler(logging.Handler):
    colours = {
        logging.DEBUG: 'white',
        logging.INFO: 'green',
        logging.WARN: 'yellow',
    }

    def emit(self, record):
        log_entry = self.format(record)
        colour = self.colours.get(record.levelno, 'red')
        click.secho(log_entry, fg=colour)


def setlogging(verbosity='medium'):
    for h in logger.handlers:
        if isinstance(h, ClickHandler):
            logger.removeHandler(h)
    handler = ClickHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if isinstance(verbosity, int):
        # to match django
        level_name = {3: 'DEBUG', 2: 'INFO'}.get(verbosity, 'WARNING')
    else:
        level_name = {'high': 'DEBUG', 'medium': 'INFO'}.get(verbosity, 'WARNING')
    level = getattr(logging, level_name)
    logger.setLevel(level)

setlogging()


class GrablibError(Exception):
    """
    Exception used when the error is clear so no traceback is required.
    """
    pass


class ProcessBase(object):
    """
    main class for downloading library files based on json file.
    """

    def __init__(self, download_root, minified_root=None, overwrite=False, file_permissions=None, sites=None):
        """
        initialize DownloadLibs.
        :param download_root: string, root folder to put files in
        :param minified_root: string, root folder for minified and concatenated files
        :param overwrite: bool, whether or not to overwrite files that already exist, default is False
        :param file_permissions: int or None, if not None permissions to give downloaded files eg. 0666
        :param sites: not used, included here to simplify argument layout in MinifyLibs
        """
        self.download_root = download_root
        self.minified_root = minified_root
        self.overwrite = overwrite
        if overwrite != DEFAULT_OPTIONS['overwrite']:
            logger.info('Overwrite set to %r' % overwrite)
        self.file_perm = file_permissions

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
