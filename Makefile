lint:
	- uv run ruff format
	- uv run ruff check
	- uv run pyright

run:
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run fastapi dev ./src/pat/main.py


test:
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run pytest

generate_migrations:
	docker compose down --remove-orphans
	docker compose run --remove-orphans -d -p "5432:5432" postgres
	uv run alembic revision --autogenerate
