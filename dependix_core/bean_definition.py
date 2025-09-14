from typing import List, Any, Optional, Type
from enum import Enum


class BeanScope(Enum):
    """Énumération pour les scopes de beans."""

    SINGLETON = "singleton"
    PROTOTYPE = "prototype"
    REQUEST = "request"
    SESSION = "session"


class BeanDefinition:
    """
    Objet de données pour stocker la configuration d'un bean.
    """

    def __init__(
        self,
        class_type: Type,
        scope: str = "singleton",
        dependencies: Optional[List[str]] = None,
        lazy: bool = False,
        factory_method: Optional[str] = None,
        init_method: Optional[str] = None,
        destroy_method: Optional[str] = None,
        constructor_args: Optional[List[Any]] = None,
        properties: Optional[dict] = None,
    ):
        self.class_type = class_type

        # Conversion du scope en BeanScope si c'est une string
        if isinstance(scope, str):
            try:
                self.scope = BeanScope(scope)
            except ValueError:
                # Pour la compatibilité, on accepte les strings non reconnues
                # mais on les convertit en SINGLETON par défaut
                self.scope = BeanScope.SINGLETON
        elif isinstance(scope, BeanScope):
            self.scope = scope
        else:
            self.scope = BeanScope.SINGLETON

        self.dependencies = dependencies if dependencies is not None else []
        self.lazy = lazy
        self.factory_method = factory_method
        self.init_method = init_method
        self.destroy_method = destroy_method
        self.constructor_args = constructor_args or []
        self.properties = properties or {}

    def __repr__(self):
        return (
            f"BeanDefinition(class_type={self.class_type.__name__}, "
            f"scope={self.scope.value}, dependencies={self.dependencies})"
        )
