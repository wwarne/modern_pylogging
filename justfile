upgrade:
  uv lock --upgrade

lint:
  uv run ruff format .
  uv run ruff check . --fix
  flake8 . --select=WPS
  uv run mypy .