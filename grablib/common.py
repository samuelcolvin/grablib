import logging
import logging.config
from typing import Union

import click

main_logger = logging.getLogger('grablib.main')
progress_logger = logging.getLogger('grablib.progress')


class ClickHandler(logging.Handler):
    formats = {
        logging.DEBUG: {'fg': 'white', 'dim': True},
        logging.INFO: {'fg': 'green'},
        logging.WARN: {'fg': 'yellow'},
    }

    def get_log_format(self, record):
        return self.formats.get(record.levelno, {'fg': 'red'})

    def emit(self, record):
        log_entry = self.format(record)
        click.secho(log_entry, **self.get_log_format(record))


class ProgressHandler(ClickHandler):
    formats = {
        logging.DEBUG: {'fg': 'white', 'dim': True},
        logging.INFO: {'fg': 'cyan'},
        logging.WARN: {'fg': 'yellow'},
    }


def log_config(log_level: Union[str, int]) -> dict:
    """
    Setup default config. for dictConfig.
    :param log_level: str name or django debugging int
    :return: dict suitable for ``logging.config.dictConfig``
    """
    if isinstance(log_level, int):
        # to match django
        log_level = {3: 'DEBUG', 2: 'INFO'}.get(log_level, 'WARNING')
    assert log_level in {'DEBUG', 'INFO', 'WARNING', 'ERROR'}, 'wrong log level %s' % log_level
    return {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'default': {'format': '%(message)s'},
            'indent': {'format': '    %(message)s'},
        },
        'handlers': {
            'default': {
                'level': log_level,
                'class': 'grablib.common.ClickHandler',
                'formatter': 'default'
            },
            'progress': {
                'level': log_level,
                'class': 'grablib.common.ProgressHandler',
                'formatter': 'indent'
            },
        },
        'loggers': {
            main_logger.name: {
                'handlers': ['default'],
                'level': log_level,
            },
            progress_logger.name: {
                'handlers': ['progress'],
                'level': log_level,
            },
        },
    }


def setup_logging(log_level):
    config = log_config(log_level)
    logging.config.dictConfig(config)


class GrablibError(RuntimeError):
    """
    Exception used when the error is clear so no traceback is required.
    """
    pass
