# dependix_core/__init__.py

from .container import Container
from .decorators import register
from .exceptions import CyclicDependencyError, DependencyNotFoundError

# On peut définir ici la version du package
__version__ = "0.1.0"

__all__ = [
    "Container",
    "register",
    "CyclicDependencyError",
    "DependencyNotFoundError",
]
