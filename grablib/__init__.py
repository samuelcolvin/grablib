from .__common__ import KnownError, DEFAULTS
from .download import DownloadLibs
from .slim import SlimLibs
from .process import process_file
from distutils.version import StrictVersion
VERSION = StrictVersion('0.0.1')

DEFAULTS = DEFAULTS.copy()
