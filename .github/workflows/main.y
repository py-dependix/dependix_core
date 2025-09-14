name: CI/CD du projet Python

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  build-and-test:
    name: Build & Test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
    - name: ⬇️ Checkout du code
      uses: actions/checkout@v4

    - name: ⚙️ Configuration de l'environnement Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: 📦 Installation des dépendances
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        # Si vous utilisez poetry, remplacez la ligne ci-dessus par :
        # pip install poetry
        # poetry install

    - name: ✅ Lancement des tests
      run: |
        pip install pytest pytest-cov
        pytest --cov=. --cov-report=xml

    - name: 🔍 Lancement du linter (Black)
      run: |
        pip install black
        black --check .

  # -------------------------------------------------------------
  
  publish-pypi:
    name: Déploiement sur PyPI
    needs: build-and-test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')

    steps:
    - name: ⬇️ Checkout du code
      uses: actions/checkout@v4

    - name: 📦 Configuration de Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.x'

    - name: ⚙️ Installation des outils de build
      run: python -m pip install --upgrade build

    - name: 🏗️ Création du package (wheel & sdist)
      run: python -m build

    - name: 🚀 Publication sur PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}