"""Module pour les exceptions personnalisées de Dependix Core.

Définit une hiérarchie d'exceptions pour gérer les erreurs
spécifiques à l'injection de dépendances.
"""


class DependixCoreError(Exception):
    """Classe de base pour toutes les exceptions de Dependix Core."""
    pass


class DependencyNotFoundError(DependixCoreError):
    """Erreur levée quand une dépendance demandée n'est pas trouvée."""

    def __init__(
        self,
        message: str,
        dependency_name: str | None = None,
        requesting_bean: str | None = None,
    ):
        self.dependency_name = dependency_name
        self.requesting_bean = requesting_bean
        super().__init__(message)


class CyclicDependencyError(DependixCoreError):
    """Erreur levée quand une dépendance cyclique est détectée."""

    def __init__(self, dependency_chain):
        self.dependency_chain = dependency_chain
        if isinstance(dependency_chain, list):
            chain_str = " -> ".join(dependency_chain)
            message = f"Dépendance cyclique détectée : {chain_str}"
        elif isinstance(dependency_chain, str):
            # Gère les chaînes de caractères directement
            message = dependency_chain
        else:
            # Fallback pour tout autre type
            message = "Dépendance cyclique détectée avec un format de chaîne inconnu."
        super().__init__(message)


class BeanInstantiationError(DependixCoreError):
    """Erreur levée lors de l'instanciation d'un bean."""

    def __init__(self, bean_name: str, original_error: Exception):
        self.bean_name = bean_name
        self.original_error = original_error
        message = (
            f"Erreur lors de l'instanciation du bean '{bean_name}': {original_error}"
        )
        super().__init__(message)


class ConfigurationError(DependixCoreError):
    """Erreur levée lors du chargement de la configuration."""

    def __init__(self, message: str, source: str | None = None):
        self.source = source
        if source:
            message = f"Erreur de configuration dans '{source}': {message}"
        super().__init__(message)


class ScopeError(DependixCoreError):
    """Erreur levée quand il y a un problème avec le scope d'un bean."""

    def __init__(self, bean_name: str, scope: str, message: str | None = None):
        self.bean_name = bean_name
        self.scope = scope
        if not message:
            message = f"Erreur de scope '{scope}' pour le bean '{bean_name}'"
        super().__init__(message)
