"""Module principal de dependix_core.

Expose les composants principaux de l'injection de dépendances,
y compris le conteneur, les décorateurs et les exceptions.
"""

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
