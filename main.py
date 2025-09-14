import os
import time  # Importation du module 'time' pour ajouter un délai
from dependix_core.container import Container
from dependix_core.decorators import (
    register,
    post_construct,
    pre_destroy,
    get_decorated_beans,
)
from dependix_core.config import load_from_yaml


# Définition de classes de test
# On utilise ici les décorateurs pour enregistrer les beans
@register(name="service_a", scope="singleton")
class ServiceA:
    def __init__(self):
        print("ServiceA a été instancié.")

    @post_construct
    def init(self):
        print("ServiceA: Méthode post-construct appelée.")
        self.is_initialized = True

    @pre_destroy
    def cleanup(self):
        print("ServiceA: Méthode pre-destroy appelée.")


@register(name="service_b")
class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a
        print("ServiceB a été instancié avec sa dépendance.")

    @post_construct
    def init(self):
        print("ServiceB: Méthode post-construct appelée.")


# Fonction pour lancer le conteneur
def main():
    container = Container()

    # 1. Chargement des beans depuis les décorateurs
    print("--- Chargement des beans décorés ---")
    # Cette ligne est essentielle pour que le conteneur connaisse vos classes décorées
    container.load_decorated_beans()

    # Récupération d'un bean décoré
    print("\n--- Test de récupération de ServiceB ---")
    # On utilise maintenant 'service_b' comme nom de bean, car le décorateur l'a enregistré ainsi.
    # Le conteneur se chargera d'injecter automatiquement 'service_a' en résolvant la dépendance par introspection.
    service_b = container.get_bean("service_b")
    print(f"ServiceB instance : {service_b}")
    print(
        f"ServiceA dans ServiceB est-il initialisé ? {service_b.service_a.is_initialized}"
    )

    # 2. Chargement des beans depuis un fichier YAML
    print("\n--- Chargement des beans via YAML ---")

    # Créez un fichier 'config.yaml' pour ce test
    # J'ai mis à jour la configuration pour qu'elle corresponde à la convention de nommage
    # et pour que 'yaml_service_b' soit bien en prototype.
    yaml_config = """
beans:
  yaml_service_a:
    class: main.ServiceA
    scope: singleton
  yaml_service_b:
    class: main.ServiceB
    scope: prototype
    """
    with open("config.yaml", "w") as f:
        f.write(yaml_config)

    load_from_yaml(container, "config.yaml")

    # Récupération d'un bean du fichier YAML
    print("\n--- Test de récupération de yaml_service_b ---")
    yaml_service_b_1 = container.get_bean("yaml_service_b")
    yaml_service_b_2 = container.get_bean("yaml_service_b")
    print(f"yaml_service_b instance 1 : {yaml_service_b_1}")
    print(f"yaml_service_b instance 2 : {yaml_service_b_2}")

    # Vérification du scope 'prototype'
    is_prototype = yaml_service_b_1 is not yaml_service_b_2
    print(f"Le scope de yaml_service_b est bien 'prototype' : {is_prototype}")

    # Arrêt du conteneur et exécution des méthodes pre-destroy
    print("\n--- Arrêt du conteneur ---")
    # J'ai ajouté un petit délai pour que vous puissiez bien voir les messages de destruction.
    time.sleep(1)
    container.shutdown()

    # Nettoyage du fichier de configuration
    os.remove("config.yaml")


if __name__ == "__main__":
    main()
