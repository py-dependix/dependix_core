# dependix-core: Un conteneur d'injection de dépendances pour Python 🐍

dependix-core est un micro-framework léger et intuitif pour l'injection de dépendances (DI) en Python. Il vous aide à gérer les dépendances de vos classes, à les instancier et à les injecter automatiquement, ce qui rend votre code plus modulaire, plus facile à tester et plus maintenable.

## 🚀 Caractéristiques principales

- **Gestion des dépendances**: Déclarez les dépendances de vos classes, et le conteneur s'occupe de les résoudre et de les injecter pour vous.

- **Décorateurs**: Utilisez des décorateurs simples pour enregistrer vos classes en tant que "beans".

- **Introspection**: Le conteneur peut résoudre automatiquement les dépendances en inspectant les annotations de type dans les constructeurs de vos classes.

- **Scopes**: Prend en charge les scopes singleton (une seule instance par conteneur) et prototype (une nouvelle instance à chaque demande).

- **Cycle de vie des beans**:
  - `@post_construct`: Exécute une méthode après l'instanciation et l'injection des dépendances d'un bean.
  - `@pre_destroy`: Exécute une méthode avant l'arrêt du conteneur pour les singletons.

- **Fichiers de configuration**: Enregistrez des beans à partir d'un fichier YAML pour une configuration externe.

- **Gestion des erreurs**: Inclut des exceptions spécifiques pour les problèmes courants comme les dépendances manquantes (`DependencyNotFoundError`) et les dépendances cycliques (`CyclicDependencyError`).

## 🛠️ Installation

```bash
pip install dependix-core
```

## 💡 Exemple d'utilisation

### Étape 1: Définir des classes et des décorateurs

Vous pouvez enregistrer vos classes en utilisant le décorateur `@register`. Si le nom n'est pas spécifié, il est généré à partir du nom de la classe en utilisant le format snake_case.

```python
from dependix_core.decorators import register, post_construct, pre_destroy

# Un bean singleton simple
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

# Un bean qui dépend de ServiceA. Le conteneur injectera ServiceA automatiquement.
@register(name="service_b")
class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a
        print("ServiceB a été instancié avec sa dépendance.")

    @post_construct
    def init(self):
        print("ServiceB: Méthode post-construct appelée.")
```

### Étape 2: Utiliser le conteneur

Le conteneur est le cœur du système. Il gère l'enregistrement et la résolution des beans.

```python
from dependix_core.container import Container
import time

def main():
    # Créez le conteneur
    container = Container()

    # Chargez les beans définis par les décorateurs
    container.load_decorated_beans()

    # Récupérez un bean
    service_b = container.get_bean("service_b")

    # Affichez un message de l'instance récupérée
    print(f"ServiceB instance: {service_b}")

    # Arrêtez le conteneur pour exécuter les méthodes pre-destroy des singletons.
    # Dans ce cas, 'cleanup' de ServiceA sera appelé.
    print("\n--- Arrêt du conteneur ---")
    time.sleep(1) # Ajoute un petit délai pour voir le message
    container.shutdown()

if __name__ == "__main__":
    main()
```

## Configuration via YAML

Vous pouvez également définir vos beans dans un fichier `config.yaml` pour séparer la configuration du code.

```yaml
# config.yaml
beans:
  yaml_service_a:
    class: main.ServiceA
    scope: singleton
  yaml_service_b:
    class: main.ServiceB
    scope: prototype
```

Ensuite, chargez ce fichier dans votre conteneur:

```python
from dependix_core.config import load_from_yaml
# ... (créez le conteneur) ...
load_from_yaml(container, "config.yaml")

# Récupérer les beans du fichier YAML
yaml_service_b_1 = container.get_bean("yaml_service_b")
yaml_service_b_2 = container.get_bean("yaml_service_b")

# Vérifiez que le scope 'prototype' fonctionne
print(f"yaml_service_b instances sont différentes ? {yaml_service_b_1 is not yaml_service_b_2}")
```

## 📚 Structure du projet

- **`dependix_core/`**: Le dossier principal du package.
  - **`__init__.py`**: Le fichier d'initialisation du package qui expose les classes et fonctions principales.
  - **`container.py`**: Le cœur du projet, gère l'enregistrement, la création et la gestion du cycle de vie des beans.
  - **`decorators.py`**: Contient les décorateurs `@register`, `@post_construct`, et `@pre_destroy`.
  - **`exceptions.py`**: Définit les exceptions personnalisées utilisées par le framework.
  - **`bean_definition.py`**: Un objet de données pour stocker la configuration d'un bean.
  - **`config.py`**: Fonctions pour charger les définitions de beans à partir d'un fichier YAML.
  - **`main.py`**: Un exemple d'utilisation complète du framework.