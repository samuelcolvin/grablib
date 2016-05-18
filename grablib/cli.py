from __future__ import unicode_literals
import logging

import click
from click import ClickException

from .common import logger, GrablibError
from .grab import grab
from .version import VERSION

click.disable_unicode_literals_warning = True


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


def setup_logging(verbosity):
    for h in logger.handlers:
        if isinstance(h, ClickHandler):
            logger.removeHandler(h)
    handler = ClickHandler()
    formatter = logging.Formatter('%(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level_name = {'high': 'DEBUG', 'medium': 'INFO', 'low': 'WARNING'}[verbosity]
    level = getattr(logging, level_name)
    logger.setLevel(level)


@click.command()
@click.version_option(VERSION, '-V', '--version')
@click.argument('action', type=click.Choice(['download', 'build']), default='download', required=False,
                metavar='[download (default) / build]')
@click.argument('config-file', type=click.Path(exists=True, dir_okay=False), default='grablib.json', required=False)
@click.option('--overwrite/--no-overwrite', default=False,
              help='Overwrite existing files, default is not to download a library if the file already exists')
@click.option('-d', '--download-root', type=click.Path(exists=False, file_okay=False),
              help='Root directory to put downloaded files in, defaults to "./static/".')
@click.option('-v', '--verbosity', type=click.Choice(['high', 'medium', 'low']), default='medium')
def cli(action, config_file, overwrite, download_root, verbosity):
    """
    Utility for defining then downloading and preprocessing external static files
    eg. Javascript, CSS.
    """
    setup_logging(verbosity)
    try:
        # other actions are not yet implemented
        grab(config_file, overwrite=overwrite, download_root=download_root)
    except GrablibError as e:
        msg = '\n{}'
        if verbosity != 'high':
            click.secho('use "--verbosity high" for more details', fg='red')
        raise ClickException(click.style(msg.format(e), fg='red'))
