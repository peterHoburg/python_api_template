fix_uv:
	uv sync --reinstall

lint: fix_uv
	- uv run ruff format
	- uv run ruff check
	- uv run pyright

run: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run fastapi dev ./src/pat/main.py


test: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run pytest

generate_migrations: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run alembic revision --autogenerate

db-init: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run python -m scripts.db_init --init

db-seed: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run python -m scripts.db_init --seed

db-setup: fix_uv
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run python -m scripts.db_init --all
