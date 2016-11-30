import sys

import click

from .common import GrablibError, setlogging
from .grab import grab
from .version import VERSION

click.disable_unicode_literals_warning = True


@click.command()
@click.version_option(VERSION, '-V', '--version')
@click.argument('action', type=click.Choice(['download', 'build']), default='download', required=False,
                metavar='[download (default) / build]')
@click.option('-f', '--config-file', type=click.Path(exists=True, dir_okay=False, file_okay=True), required=False)
@click.option('-v', '--verbosity', type=click.Choice(['high', 'medium', 'low']), default='medium')
def cli(action, config_file, verbosity):
    """
    Utility for defining then downloading and preprocessing external static files
    eg. Javascript, CSS.
    """
    setlogging(verbosity)
    try:
        # other actions are not yet implemented
        grab(config_file=config_file)
    except GrablibError as e:
        if verbosity != 'high':
            click.secho('use "--verbosity high" for more details', fg='red')
        click.secho('Error: %s' % e, fg='red')
        sys.exit(2)
