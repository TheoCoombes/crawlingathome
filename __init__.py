from .version import PrintVersion as _printversion
_printversion()

from .core import init
from .recycler import dump, load
from .version import VERSION as __version__
