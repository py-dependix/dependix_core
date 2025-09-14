# dependix_core/config.py

import yaml
import importlib
from .container import Container
from .exceptions import DependencyNotFoundError


def load_from_yaml(container: Container, file_path: str):
    """
    Charge les définitions de beans depuis un fichier YAML et les enregistre dans le conteneur.

    Args:
        container (Container): L'instance du conteneur dans laquelle les beans doivent être enregistrés.
        file_path (str): Le chemin vers le fichier de configuration YAML.
    """
    try:
        with open(file_path, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Le fichier de configuration YAML n'a pas été trouvé à '{file_path}'."
        )
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Erreur de syntaxe dans le fichier YAML : {e}")

    beans_config = config.get("beans", {})
    if not isinstance(beans_config, dict):
        raise TypeError(
            "Le bloc 'beans' dans le fichier YAML doit être un dictionnaire."
        )

    for name, bean_config in beans_config.items():
        class_path = bean_config.get("class")
        if not class_path:
            raise ValueError(f"La clé 'class' est manquante pour le bean '{name}'.")

        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            class_type = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Impossible d'importer la classe '{class_path}' pour le bean '{name}' : {e}"
            )

        scope = bean_config.get("scope", "singleton")
        dependencies = bean_config.get("dependencies", [])

        # Validation des dépendances pour s'assurer qu'elles sont dans un format attendu
        if not isinstance(dependencies, list):
            raise TypeError(f"Les dépendances du bean '{name}' doivent être une liste.")

        container.register_bean(name, class_type, scope, dependencies)
