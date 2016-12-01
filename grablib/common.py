import logging
import os

import click
from pathlib import Path

logger = logging.getLogger('grablib')

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


class GrablibError(RuntimeError):
    """
    Exception used when the error is clear so no traceback is required.
    """
    pass
