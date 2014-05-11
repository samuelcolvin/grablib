import re
from .__common__ import DEFAULT_VERBOSITY, cprint, colour_lookup, KnownError, DEFAULTS, ProcessBase
try:
    from slimit import minify
except:
    SLIM_OK = False
else:
    SLIM_OK = True

class Slim(ProcessBase):
    def __init__(self, slim_settings, libs_root_slim, libs_root, sites = None, **kw):
        """
        initialize Slim.
        Args:
            slim_settings: definition of slim process
            
            libs_root_slim: root directory to put slimmed files in.
        """
        super(Slim, self).__init__(libs_root, **kw)
        self. slim_settings = slim_settings
        self. libs_root_slim = libs_root_slim