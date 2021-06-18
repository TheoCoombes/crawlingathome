from .version import PrintVersion
PrintVersion()

from .core import init
from .recycler import dump, load
from .version import VERSION as __version__
