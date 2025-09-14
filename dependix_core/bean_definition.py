"""Module pour la définition de la classe BeanDefinition et BeanScope.

Ces classes sont utilisées pour la configuration des beans dans le conteneur d'injection.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from enum import Enum


class BeanScope(Enum):
    """Énumération pour les scopes de beans."""

    SINGLETON = "singleton"
    PROTOTYPE = "prototype"
    REQUEST = "request"
    SESSION = "session"


@dataclass
class BeanDefinition:
    """
    Objet de données pour stocker la configuration d'un bean.
    """
    class_type: Type
    scope: BeanScope = BeanScope.SINGLETON
    dependencies: List[str] = field(default_factory=list)
    lazy: bool = False
    factory_method: Optional[str] = None
    init_method: Optional[str] = None
    destroy_method: Optional[str] = None
    constructor_args: List[Any] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Méthode appelée après l'initialisation du dataclass."""
        if isinstance(self.scope, str):
            try:
                self.scope = BeanScope(self.scope)
            except ValueError:
                self.scope = BeanScope.SINGLETON

    def __repr__(self) -> str:
        """
        Représentation string pour le débogage.
        """
        return (
            f"BeanDefinition(class_type={self.class_type.__name__}, "
            f"scope={self.scope.value}, dependencies={self.dependencies})"
        )
