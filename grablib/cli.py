import sys

import click

from .common import GrablibError, setup_logging
from .grab import Grab
from .version import VERSION

click.disable_unicode_literals_warning = True


@click.command()
@click.version_option(VERSION, '-V', '--version')
@click.argument('action', type=click.Choice(['download', 'build']), required=False, metavar='[download / build]')
@click.option('-f', '--config-file', type=click.Path(exists=True, dir_okay=False, file_okay=True), required=False)
@click.option('--no-debug/--debug', 'debug', default=None)
@click.option('-v/-q', '--verbose/--quiet', 'verbose', default=None)
def cli(action, config_file, debug, verbose):
    """
    Static asset management in python.

    Called with no arguments grablib will download, then build. You can also choose to only download or build.

    See `grablib -h` and https://github.com/samuelcolvin/grablib for more help.
    """
    if verbose is True:
        log_level = 'DEBUG'
    elif verbose is False:
        log_level = 'WARNING'
    else:
        assert verbose is None
        log_level = 'INFO'

    setup_logging(log_level)
    try:
        grab = Grab(config_file, debug=debug)
        if action in {'download', None}:
            grab.download()
        if action in {'build', None}:
            grab.build()
    except GrablibError as e:
        click.secho('Error: %s' % e, fg='red')
        sys.exit(2)
