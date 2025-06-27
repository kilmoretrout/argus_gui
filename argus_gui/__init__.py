#!/usr/bin/env python

from __future__ import absolute_import

from .version import __version__

# Export public API
__all__ = ['__version__', 'resources']

# load submodules conditionally to avoid import errors during module discovery
try:
    from .colors import *
    from .logger import *
    from .output import *
    from .patterns import *
    from .sbaDriver import *
    from .sync import *
    from .tools import *
    from .triangulate import *
    from .undistort import *
    from .frameFinderPyglet import *
    # Import graphers and Argus last as they depend on PySide6
    from .graphers import *
    from .Argus import *
except ImportError:
    # If dependencies aren't available, skip the imports
    # This prevents module discovery warnings
    pass

# Resources are always available
from . import resources
