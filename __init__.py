from .version import PrintVersion as _printversion
_printversion()

from .core import init, print, Client
from .version import VERSION as __version__
from .errors import *
