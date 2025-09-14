"""
Conteneur principal pour la gestion de l'injection de dépendances.

Ce module définit la classe `Container`, le cœur de la bibliothèque,
responsable de l'enregistrement, de la résolution et de la gestion
du cycle de vie des beans.
"""

import inspect
import sys
import threading
from typing import Any, Dict, List, Optional, Type, TypeVar, get_type_hints

from .bean_definition import BeanDefinition, BeanScope
from .decorators import (
    get_decorated_beans,
    get_post_construct_methods,
    get_pre_destroy_methods,
)
from .exceptions import (
    BeanInstantiationError,
    CyclicDependencyError,
    DependencyNotFoundError,
)

T = TypeVar("T")


class Container:
    """
    Conteneur IoC principal pour la gestion des dépendances.
    """

    def __init__(self):
        self._definitions: Dict[str, BeanDefinition] = {}
        self._singletons: Dict[str, Any] = {}
        self._resolving_stack: List[str] = []
        self._lock = threading.RLock()
        self._is_shutdown = False
        self._class_to_bean_name: Dict[Type, str] = {}

    def register_bean(
        self,
        name: str,
        class_type: Type,
        scope: str = "singleton",
        dependencies: Optional[List[str]] = None,
    ):
        """Enregistre un bean dans le conteneur (compatible avec l'API existante)."""
        if self._is_shutdown:
            raise RuntimeError("Le conteneur est arrêté")

        if name in self._definitions:
            raise ValueError(f"A bean with the name '{name}' is already registered.")

        self._definitions[name] = BeanDefinition(class_type, scope, dependencies)
        self._class_to_bean_name[class_type] = name

    def register_bean_definition(self, name: str, definition: BeanDefinition) -> None:
        """Enregistre une définition de bean directement."""
        if self._is_shutdown:
            raise RuntimeError("Le conteneur est arrêté")

        if name in self._definitions:
            raise ValueError(f"Un bean avec le nom '{name}' est déjà enregistré.")

        self._definitions[name] = definition
        self._class_to_bean_name[definition.class_type] = name

    def load_decorated_beans(self):
        """Charge tous les beans décorés dans le conteneur."""
        decorated_beans = get_decorated_beans()
        for name, config in decorated_beans.items():
            if name not in self._definitions:  # Éviter les doublons
                self.register_bean(
                    name=name,
                    class_type=config["class_type"],
                    scope=config["scope"],
                    dependencies=config["dependencies"],
                )
        self._validate_dependencies()

    def get_bean(self, name: str) -> Any:
        """Récupère un bean par son nom (compatible avec l'API existante)."""
        if self._is_shutdown:
            raise RuntimeError("Le conteneur est arrêté")

        if name not in self._definitions:
            raise DependencyNotFoundError(f"Bean with name '{name}' not found.", name)

        definition = self._definitions[name]

        if definition.scope == BeanScope.SINGLETON:
            if name not in self._singletons:
                with self._lock:
                    if name not in self._singletons:
                        self._singletons[name] = self._create_bean_instance(definition)
            return self._singletons[name]

        # Prototype scope
        return self._create_bean_instance(definition)

    def _resolve_dependencies(self, class_type: Type) -> Dict[str, Type]:
        """Résout automatiquement les dépendances via l'introspection."""
        if not hasattr(class_type, "__init__") or not inspect.isfunction(
            class_type.__init__
        ):
            return {}

        # Gère les références anticipées de type (annotations en tant que chaînes)
        # en utilisant le module sys pour un import robuste.
        try:
            type_hints = get_type_hints(class_type.__init__, localns={
                class_type.__name__: class_type
            }, globalns=sys.modules[class_type.__module__].__dict__)
        except NameError as exc:
            # Fallback pour les cas plus complexes
            signature = inspect.signature(class_type.__init__)
            type_hints = {
                p.name: p.annotation
                for p in signature.parameters.values()
                if p.annotation != inspect.Parameter.empty
            }

        dependencies_map = {}
        for param_name, param_type in type_hints.items():
            if param_name == "self":
                continue

            if isinstance(param_type, str):
                param_type = getattr(sys.modules[class_type.__module__], param_type, None)

            if param_type and param_type in self._class_to_bean_name:
                dependencies_map[param_name] = param_type
            else:
                raise DependencyNotFoundError(
                    f"Dépendance '{param_name}' pour le type '{param_type}' non trouvée."
                )

        return dependencies_map

    def _create_bean_instance(self, definition: BeanDefinition):
        """Crée une instance de bean avec gestion des dépendances."""
        class_name = definition.class_type.__name__
        if class_name in self._resolving_stack:
            cycle = self._resolving_stack + [class_name]
            raise CyclicDependencyError(cycle)

        self._resolving_stack.append(class_name)

        try:
            dependencies_map = {}
            if definition.dependencies:
                # Si les dépendances sont spécifiées explicitement, on les résout
                for dep_name in definition.dependencies:
                    dep_instance = self.get_bean(dep_name)
                    dependencies_map[dep_name] = dep_instance
            else:
                # Sinon, on utilise l'introspection
                dependencies_to_resolve = self._resolve_dependencies(
                    definition.class_type
                )
                for param_name, dep_class_type in dependencies_to_resolve.items():
                    dep_bean_name = self._class_to_bean_name[dep_class_type]
                    dep_instance = self.get_bean(dep_bean_name)
                    dependencies_map[param_name] = dep_instance

            # Création de l'instance avec les dépendances résolues
            instance = definition.class_type(**dependencies_map)

            # Exécution de la méthode post-construct
            post_construct_methods = get_post_construct_methods()
            for method_qualname, method_ref in post_construct_methods.items():
                if method_qualname.startswith(f"{definition.class_type.__name__}."):
                    method_name = method_ref.__name__
                    method = getattr(instance, method_name, None)
                    if method and callable(method):
                        method()

            self._resolving_stack.pop()
            return instance
        except Exception as exc:
            self._resolving_stack.pop()
            if isinstance(exc, (CyclicDependencyError, DependencyNotFoundError)):
                raise
            raise BeanInstantiationError(class_name, exc) from exc

    def _validate_dependencies(self):
        """Valide toutes les dépendances enregistrées au démarrage."""
        for name, definition in self._definitions.items():
            dependencies_to_check = definition.dependencies
            if not dependencies_to_check:
                try:
                    dependencies_to_check = self._resolve_dependencies(
                        definition.class_type
                    )
                except DependencyNotFoundError as exc:
                    raise DependencyNotFoundError(
                        f"Dépendance '{exc.dependency_name}' pour le bean '{name}' non trouvée. "
                        "Veuillez enregistrer ce bean ou corriger l'orthographe.",
                        exc.dependency_name,
                        name,
                    ) from exc

            for dep_name in dependencies_to_check:
                if dep_name not in self._definitions:
                    raise DependencyNotFoundError(
                        f"Dépendance '{dep_name}' pour le bean '{name}' non trouvée. "
                        "Veuillez enregistrer ce bean ou corriger l'orthographe.",
                        dep_name,
                        name,
                    )

    def has_bean(self, name: str) -> bool:
        """Vérifie si un bean existe."""
        return name in self._definitions

    def list_beans(self) -> Dict[str, str]:
        """Liste tous les beans enregistrés avec leur type."""
        return {
            name: definition.class_type.__name__
            for name, definition in self._definitions.items()
        }

    def get_bean_definition(self, name: str) -> BeanDefinition:
        """Récupère la définition d'un bean."""
        if name not in self._definitions:
            raise DependencyNotFoundError(f"Bean '{name}' non trouvé", name)
        return self._definitions[name]

    def shutdown(self):
        """Arrête le conteneur et exécute les méthodes de pré-destruction pour les singletons."""
        if self._is_shutdown:
            return

        self._is_shutdown = True

        pre_destroy_methods = get_pre_destroy_methods()
        for name, instance in list(self._singletons.items()):
            try:
                for method_qualname, method_ref in pre_destroy_methods.items():
                    if method_qualname.startswith(f"{instance.__class__.__name__}."):
                        method_name = method_ref.__name__
                        method = getattr(instance, method_name, None)
                        if method and callable(method):
                            method()
            except Exception as e:
                print(f"Erreur lors de la destruction du bean '{name}': {e}")

        self._singletons.clear()

    def __enter__(self):
        """Support du context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Arrêt automatique lors de la sortie du context manager."""
        self.shutdown()