upgrade:
  uv lock --upgrade

lint:
  uv run ruff format .
  uv run ruff check . --fix
  uv run flake8 . --select=WPS
  uv run mypy .

test:
  uv run pytest tests