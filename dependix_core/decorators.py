import functools
import re
from typing import Dict, Any, List

# Variable globale pour stocker les informations des beans décorés
_decorated_beans: Dict[str, Dict[str, Any]] = {}
_post_construct_methods = {}
_pre_destroy_methods = {}


def _reset_decorated_beans():
    """Réinitialise les informations des beans décorés."""
    _decorated_beans.clear()
    _post_construct_methods.clear()
    _pre_destroy_methods.clear()


def get_decorated_beans():
    """Retourne la liste des beans décorés."""
    return _decorated_beans


def get_post_construct_methods():
    """Retourne la liste des méthodes post-construct."""
    return _post_construct_methods


def get_pre_destroy_methods():
    """Retourne la liste des méthodes pre-destroy."""
    return _pre_destroy_methods


def register(
    name: str = None, scope: str = "singleton", dependencies: List[str] = None
):
    """
    Décorateur pour enregistrer une classe en tant que bean.
    Le nom par défaut est la version en snake_case du nom de la classe.
    """

    def decorator(cls):
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

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)

    wrapper.__post_construct__ = True
    _post_construct_methods[f"{method.__qualname__}"] = method
    return wrapper


def pre_destroy(method):
    """
    Décorateur pour marquer une méthode comme "pre-destroy".
    """

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)

    wrapper.__pre_destroy__ = True
    _pre_destroy_methods[f"{method.__qualname__}"] = method
    return wrapper
