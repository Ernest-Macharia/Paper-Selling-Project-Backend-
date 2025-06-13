#!/bin/bash

echo "Setting up development environment..."

python -m pip install --upgrade pip
pip install black isort flake8 bandit pre-commit

pre-commit install

git config --global alias.smart-commit '!pre-commit run --all-files && git add . && git commit'
echo "Pre-commit hooks installed."
echo "You're ready to code safely 🎯"
