"""
Module pour les décorateurs d'injection de dépendances.

Fournit des décorateurs pour marquer les classes en tant que beans
et définir des méthodes de cycle de vie (`post_construct` et `pre_destroy`).
"""

import functools
import re
from typing import Dict, Any, List, Type

# Variables globales pour stocker les informations des beans décorés
_decorated_beans: Dict[str, Dict[str, Any]] = {}
_post_construct_methods: Dict[str, Any] = {}
_pre_destroy_methods: Dict[str, Any] = {}


def _reset_decorated_beans():
    """Réinitialise les informations des beans décorés pour les tests."""
    _decorated_beans.clear()
    _post_construct_methods.clear()
    _pre_destroy_methods.clear()


def get_decorated_beans() -> Dict[str, Dict[str, Any]]:
    """Retourne la liste des beans décorés."""
    return _decorated_beans


def get_post_construct_methods() -> Dict[str, Any]:
    """Retourne la liste des méthodes post-construct."""
    return _post_construct_methods


def get_pre_destroy_methods() -> Dict[str, Any]:
    """Retourne la liste des méthodes pre-destroy."""
    return _pre_destroy_methods


def register(
    name: str | None = None, scope: str = "singleton", dependencies: List[str] | None = None
):
    """
    Décorateur pour enregistrer une classe en tant que bean.
    Le nom par défaut est la version en snake_case du nom de la classe.
    """

    def decorator(cls: Type[Any]):
        bean_name = name
        if bean_name is None:
            # Conversion du nom de la classe en snake_case
            bean_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

        _decorated_beans[bean_name] = {
            "class_type": cls,
            "scope": scope,
            "dependencies": dependencies,
        }
        return cls

    return decorator


def post_construct(method):
    """
    Décorateur pour marquer une méthode comme "post-construct".
    """
    _post_construct_methods[f"{method.__qualname__}"] = method

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)

    return wrapper


def pre_destroy(method):
    """
    Décorateur pour marquer une méthode comme "pre-destroy".
    """
    _pre_destroy_methods[f"{method.__qualname__}"] = method

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)

    return wrapper