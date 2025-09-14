"""
Tests unitaires pour le conteneur d'injection de dépendances dependix_core.

Ce module contient des tests pour valider le bon fonctionnement de la
classe Container, des décorateurs d'enregistrement, et de la gestion
des dépendances.
"""
import os
import tempfile
import sys
from unittest.mock import patch, MagicMock

import pytest
import yaml

# Import des modules à tester
from dependix_core.container import Container
from dependix_core.bean_definition import BeanDefinition, BeanScope
from dependix_core.decorators import (
    register,
    post_construct,
    pre_destroy,
    _reset_decorated_beans,
    get_decorated_beans,
    get_post_construct_methods,
    get_pre_destroy_methods,
)
from dependix_core.exceptions import (
    DependencyNotFoundError,
    CyclicDependencyError,
    BeanInstantiationError,
    ConfigurationError,
    ScopeError,
)
from dependix_core.config import load_from_yaml


# Classes de test
class SimpleService:
    """Service simple sans dépendances."""

    def __init__(self):
        self.initialized = True
        self.post_construct_called = False
        self.pre_destroy_called = False


class DatabaseService:
    """Service de base de données."""

    def __init__(self):
        self.connected = True


class UserService:
    """Service utilisateur avec dépendance."""

    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.post_construct_called = False

    def get_users(self):
        """Récupère une liste d'utilisateurs."""
        return ["user1", "user2"] if self.database_service.connected else []


class EmailService:
    """Service email avec dépendance."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def send_newsletter(self):
        """Envoie une newsletter à tous les utilisateurs."""
        users = self.user_service.get_users()
        return f"Newsletter envoyée à {len(users)} utilisateurs"


# Services avec dépendance cyclique pour les tests
class ServiceA:
    """Un service A qui dépend du service B."""
    def __init__(self, service_b: "ServiceB"):
        self.service_b = service_b


class ServiceB:
    """Un service B qui dépend du service A."""
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a


# Services décorés pour les tests
@register(name="decorated_simple", scope="singleton")
class DecoratedSimpleService:
    """Un service simple décoré."""
    def __init__(self):
        self.value = "decorated"
        self.post_construct_called = False
        self.pre_destroy_called = False

    @post_construct
    def init_method(self):
        """Méthode post-construct pour initialisation."""
        self.post_construct_called = True

    @pre_destroy
    def cleanup_method(self):
        """Méthode pre-destroy pour le nettoyage."""
        self.pre_destroy_called = True


@register(scope="prototype")
class DecoratedDependencyService:
    """Un service décoré avec une dépendance décorée."""
    def __init__(self, decorated_simple: DecoratedSimpleService):
        self.decorated_simple = decorated_simple


@register(name="lifecycle_service")
class LifecycleService:
    """Un service pour tester le cycle de vie."""
    def __init__(self):
        self.state = "created"

    @post_construct
    def initialize(self):
        """Initialise le service."""
        self.state = "initialized"

    @pre_destroy
    def cleanup(self):
        """Nettoie le service."""
        self.state = "destroyed"


class TestBeanDefinition:
    """Tests pour la classe BeanDefinition."""

    def test_bean_definition_creation(self):
        """Test de création d'une BeanDefinition."""
        definition = BeanDefinition(
            class_type=SimpleService,
            scope="singleton",
            dependencies=["dep1", "dep2"],
            lazy=True,
        )

        assert definition.class_type == SimpleService
        assert definition.scope == BeanScope.SINGLETON
        assert definition.dependencies == ["dep1", "dep2"]
        assert definition.lazy is True

    def test_bean_definition_scope_conversion(self):
        """Test de conversion des scopes."""
        # Test avec enum
        definition = BeanDefinition(SimpleService, BeanScope.PROTOTYPE)
        assert definition.scope == BeanScope.PROTOTYPE

        # Test avec string valide
        definition = BeanDefinition(SimpleService, "prototype")
        assert definition.scope == BeanScope.PROTOTYPE

        # Test avec string invalide (doit fallback à SINGLETON)
        definition = BeanDefinition(SimpleService, "invalid_scope")
        assert definition.scope == BeanScope.SINGLETON

    def test_bean_definition_repr(self):
        """Test de la représentation string."""
        definition = BeanDefinition(SimpleService, "singleton", ["dep1"])
        repr_str = repr(definition)

        assert "BeanDefinition" in repr_str
        assert "SimpleService" in repr_str
        assert "singleton" in repr_str
        assert "dep1" in repr_str


class TestContainer:
    """Tests pour la classe Container."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.container = Container()

    def teardown_method(self):
        """Cleanup après chaque test."""
        if hasattr(self, "container"):
            self.container.shutdown()

    def test_register_bean_simple(self):
        """Test d'enregistrement d'un bean simple."""
        self.container.register_bean("simple", SimpleService)

        assert self.container.has_bean("simple")
        assert "simple" in self.container.list_beans()
        assert self.container.list_beans()["simple"] == "SimpleService"

    def test_register_bean_duplicate_error(self):
        """Test d'erreur lors de l'enregistrement d'un bean dupliqué."""
        self.container.register_bean("simple", SimpleService)

        with pytest.raises(ValueError, match="already registered"):
            self.container.register_bean("simple", SimpleService)

    def test_get_bean_singleton(self):
        """Test de récupération d'un bean singleton."""
        self.container.register_bean("simple", SimpleService)

        instance1 = self.container.get_bean("simple")
        instance2 = self.container.get_bean("simple")

        assert isinstance(instance1, SimpleService)
        assert instance1 is instance2
        assert instance1.initialized

    def test_get_bean_prototype(self):
        """Test de récupération d'un bean prototype."""
        self.container.register_bean("simple", SimpleService, scope="prototype")

        instance1 = self.container.get_bean("simple")
        instance2 = self.container.get_bean("simple")

        assert isinstance(instance1, SimpleService)
        assert isinstance(instance2, SimpleService)
        assert instance1 is not instance2

    def test_get_bean_not_found(self):
        """Test d'erreur quand un bean n'existe pas."""
        with pytest.raises(DependencyNotFoundError):
            self.container.get_bean("nonexistent")

    def test_dependency_injection_manual(self):
        """Test d'injection de dépendances manuel."""
        self.container.register_bean("database_service", DatabaseService)
        self.container.register_bean(
            "user", UserService, dependencies=["database_service"]
        )

        user_service = self.container.get_bean("user")

        assert isinstance(user_service, UserService)
        assert isinstance(user_service.database_service, DatabaseService)
        assert user_service.database_service.connected

    def test_dependency_injection_automatic(self):
        """Test d'injection de dépendances automatique."""
        self.container.register_bean("database_service", DatabaseService)
        self.container.register_bean("user_service", UserService)

        user_service = self.container.get_bean("user_service")

        assert isinstance(user_service, UserService)
        assert isinstance(user_service.database_service, DatabaseService)

    def test_chain_dependency_injection(self):
        """Test d'injection de dépendances en chaîne."""
        self.container.register_bean("database_service", DatabaseService)
        self.container.register_bean("user_service", UserService)
        self.container.register_bean("email_service", EmailService)

        email_service = self.container.get_bean("email_service")

        assert isinstance(email_service, EmailService)
        assert isinstance(email_service.user_service, UserService)
        assert isinstance(email_service.user_service.database_service, DatabaseService)

        result = email_service.send_newsletter()
        assert "2 utilisateurs" in result

    def test_cyclic_dependency_detection(self):
        """Test de détection des dépendances cycliques."""
        self.container.register_bean("service_a", ServiceA)
        self.container.register_bean("service_b", ServiceB)

        with pytest.raises(CyclicDependencyError):
            self.container.get_bean("service_a")

    def test_register_bean_definition(self):
        """Test d'enregistrement d'une définition de bean."""
        definition = BeanDefinition(
            class_type=SimpleService, scope="prototype", lazy=True
        )

        self.container.register_bean_definition("simple", definition)

        assert self.container.has_bean("simple")
        retrieved_def = self.container.get_bean_definition("simple")
        assert retrieved_def.scope == BeanScope.PROTOTYPE
        assert retrieved_def.lazy is True

    def test_load_decorated_beans(self):
        """Test du chargement des beans décorés."""
        # Les classes sont maintenant définies globalement
        self.container.load_decorated_beans()

        assert self.container.has_bean("decorated_simple")
        assert self.container.has_bean("decorated_dependency_service")

        # Test du bean simple décoré
        simple = self.container.get_bean("decorated_simple")
        assert isinstance(simple, DecoratedSimpleService)
        assert simple.value == "decorated"
        assert simple.post_construct_called

        # Test du bean avec dépendance
        dependency_service = self.container.get_bean("decorated_dependency_service")
        assert isinstance(dependency_service, DecoratedDependencyService)
        assert dependency_service.decorated_simple is simple

    def test_context_manager(self):
        """Test du context manager."""
        with Container() as container:
            container.register_bean("simple", SimpleService)
            simple = container.get_bean("simple")
            assert isinstance(simple, SimpleService)

        # Le conteneur doit être arrêté
        assert container._is_shutdown

    def test_shutdown_calls_pre_destroy(self):
        """Test que shutdown appelle les méthodes pre-destroy."""
        # La classe est maintenant définie globalement
        self.container.load_decorated_beans()
        simple = self.container.get_bean("decorated_simple")

        # Le test doit passer car init_method a été appelé lors de get_bean
        assert simple.post_construct_called

        assert not simple.pre_destroy_called
        self.container.shutdown()
        assert simple.pre_destroy_called

    def test_operation_after_shutdown(self):
        """Test que les opérations après shutdown lèvent une erreur."""
        self.container.shutdown()

        with pytest.raises(RuntimeError, match="arrêté"):
            self.container.register_bean("test", SimpleService)

        with pytest.raises(RuntimeError, match="arrêté"):
            self.container.get_bean("test")


class TestDecorators:
    """Tests pour les décorateurs."""

    def setup_method(self):
        """Setup avant chaque test."""
        _reset_decorated_beans()

    def test_register_decorator_with_name(self):
        """Test du décorateur register avec nom explicite."""

        @register(name="custom_name", scope="prototype")
        class TestService:
            pass
        
        beans = get_decorated_beans()

        assert "custom_name" in beans
        assert beans["custom_name"]["class_type"] == TestService
        assert beans["custom_name"]["scope"] == "prototype"

    def test_register_decorator_auto_name(self):
        """Test du décorateur register avec nom automatique."""

        @register()
        class AutoNamedService:
            pass

        beans = get_decorated_beans()

        assert "auto_named_service" in beans
        assert beans["auto_named_service"]["class_type"] == AutoNamedService

    def test_post_construct_decorator(self):
        """Test du décorateur post_construct."""

        class TestService:
            def __init__(self):
                self.initialized = False

            @post_construct
            def init(self):
                """Initialise le service."""
                self.initialized = True

        methods = get_post_construct_methods()

        assert any("TestService.init" in key for key in methods)

        # Test fonctionnel
        service = TestService()
        assert not service.initialized
        service.init()
        assert service.initialized

    def test_pre_destroy_decorator(self):
        """Test du décorateur pre_destroy."""

        class TestService:
            def __init__(self):
                self.cleaned = False

            @pre_destroy
            def cleanup(self):
                """Nettoie le service."""
                self.cleaned = True

        methods = get_pre_destroy_methods()
        assert any("TestService.cleanup" in key for key in methods)


class TestConfig:
    """Tests pour le chargement de configuration YAML."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.container = Container()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup après chaque test."""
        self.container.shutdown()
        # Nettoyage du répertoire temporaire
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def create_temp_yaml(self, content):
        """Crée un fichier YAML temporaire."""
        file_path = os.path.join(self.temp_dir, "config.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_load_from_yaml_success(self):
        """Test de chargement réussi depuis YAML."""
        yaml_content = """
beans:
  simple_service:
    class: dependix_core.tests.test_container.SimpleService
    scope: singleton
  database_service:
    class: dependix_core.tests.test_container.DatabaseService
    scope: singleton
"""
        config_file = self.create_temp_yaml(yaml_content)

        load_from_yaml(self.container, config_file)

        assert self.container.has_bean("simple_service")
        assert self.container.has_bean("database_service")

        simple = self.container.get_bean("simple_service")
        assert isinstance(simple, SimpleService)

    def test_load_from_yaml_file_not_found(self):
        """Test d'erreur quand le fichier YAML n'existe pas."""
        with pytest.raises(FileNotFoundError):
            load_from_yaml(self.container, "nonexistent.yaml")

    def test_load_from_yaml_invalid_yaml(self):
        """Test d'erreur avec YAML invalide."""
        yaml_content = """
beans:
  simple_service:
    class: dependix_core.tests.test_container.SimpleService
    scope: singleton
    invalid_yaml: [unclosed
"""
        config_file = self.create_temp_yaml(yaml_content)

        with pytest.raises(yaml.YAMLError):
            load_from_yaml(self.container, config_file)

    def test_load_from_yaml_missing_class(self):
        """Test d'erreur quand la clé 'class' manque."""
        yaml_content = """
beans:
  simple_service:
    scope: singleton
"""
        config_file = self.create_temp_yaml(yaml_content)

        with pytest.raises(ValueError, match="La clé 'class' est manquante"):
            load_from_yaml(self.container, config_file)

    def test_load_from_yaml_invalid_class(self):
        """Test d'erreur avec classe invalide."""
        yaml_content = """
beans:
  simple_service:
    class: nonexistent.module.NonExistentClass
"""
        config_file = self.create_temp_yaml(yaml_content)

        with pytest.raises(ImportError):
            load_from_yaml(self.container, config_file)

    def test_load_from_yaml_with_dependencies(self):
        """Test de chargement avec dépendances."""
        yaml_content = """
beans:
  database_service:
    class: dependix_core.tests.test_container.DatabaseService
    scope: singleton
  user_service:
    class: dependix_core.tests.test_container.UserService
    dependencies: [database_service]
"""
        config_file = self.create_temp_yaml(yaml_content)

        load_from_yaml(self.container, config_file)

        user_service = self.container.get_bean("user_service")
        assert isinstance(user_service, UserService)
        assert isinstance(user_service.database_service, DatabaseService)


class TestExceptions:
    """Tests pour les exceptions personnalisées."""

    def test_dependency_not_found_error(self):
        """Test de DependencyNotFoundError."""
        error = DependencyNotFoundError(
            "Dependency not found",
            dependency_name="missing_dep",
            requesting_bean="requesting_bean",
        )

        assert error.dependency_name == "missing_dep"
        assert error.requesting_bean == "requesting_bean"
        assert "Dependency not found" in str(error)

    def test_cyclic_dependency_error_with_list(self):
        """Test de CyclicDependencyError avec liste."""
        chain = ["ServiceA", "ServiceB", "ServiceA"]
        error = CyclicDependencyError(chain)

        assert error.dependency_chain == chain
        assert "ServiceA -> ServiceB -> ServiceA" in str(error)

    def test_cyclic_dependency_error_with_string(self):
        """Test de CyclicDependencyError avec string (compatibilité)."""
        error = CyclicDependencyError("Custom cycle message")
        assert "Custom cycle message" in str(error)

    def test_bean_instantiation_error(self):
        """Test de BeanInstantiationError."""
        original_error = ValueError("Original error")
        error = BeanInstantiationError("test_bean", original_error)

        assert error.bean_name == "test_bean"
        assert error.original_error is original_error
        assert "test_bean" in str(error)
        assert "Original error" in str(error)

    def test_configuration_error(self):
        """Test de ConfigurationError."""
        error = ConfigurationError("Config error", source="config.yaml")

        assert error.source == "config.yaml"
        assert "config.yaml" in str(error)
        assert "Config error" in str(error)

    def test_scope_error(self):
        """Test de ScopeError."""
        error = ScopeError("test_bean", "invalid_scope", "Custom message")

        assert error.bean_name == "test_bean"
        assert error.scope == "invalid_scope"
        assert "Custom message" in str(error)

        # Test avec message par défaut
        error2 = ScopeError("test_bean", "invalid_scope")
        assert "invalid_scope" in str(error2)


class TestIntegration:
    """Tests d'intégration complets."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.container = Container()

    def teardown_method(self):
        """Cleanup après chaque test."""
        self.container.shutdown()
        # _reset_decorated_beans() # Ligne à supprimer

    def test_mixed_registration_methods(self):
        """Test de mélange entre enregistrement manuel et décorateurs."""
        # Enregistrement manuel
        self.container.register_bean("database", DatabaseService)

        # Beans décorés
        @register(name="user_service")
        class UserServiceDecorated:
            def __init__(self, database: DatabaseService):
                self.database = database

        self.container.load_decorated_beans()

        # Test que tout fonctionne ensemble
        user_service = self.container.get_bean("user_service")
        assert isinstance(user_service, UserServiceDecorated)
        assert isinstance(user_service.database, DatabaseService)

    def test_complex_dependency_graph(self):
        """Test d'un graphe de dépendances complexe."""
        self.container.register_bean("database_service", DatabaseService)
        self.container.register_bean("user_service", UserService)
        self.container.register_bean("email_service", EmailService)

        # Ajout d'un service qui dépend d'email
        class NotificationService:
            def __init__(self, email_service: EmailService):
                self.email_service = email_service

            def notify_all(self):
                """Envoie des notifications."""
                return f"Notifications: {self.email_service.send_newsletter()}"

        self.container.register_bean("notification_service", NotificationService)

        # Test de la chaîne complète
        notification = self.container.get_bean("notification_service")
        result = notification.notify_all()

        assert "Notifications:" in result
        assert "2 utilisateurs" in result


if __name__ == "__main__":
    _reset_decorated_beans()  # Réinitialiser une seule fois avant de lancer tous les tests
    pytest.main([__file__, "-v"])
