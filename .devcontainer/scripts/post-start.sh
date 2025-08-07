#!/bin/bash

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

if [ -f "pyproject.toml" ]; then
    echo "Installing dependencies..."
    uv sync
fi

echo "Installing pre-commit..."
uv run pre-commit install

echo "Post-create script completed successfully."
