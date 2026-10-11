.PHONY: help up down test test-tri test-api test-worker test-inep migrate seed build

help:
	@echo "ENEM Intelligence - Comandos de Automação:"
	@echo "  make up         - Sobe os serviços completos via Docker Compose"
	@echo "  make down       - Encerra os serviços"
	@echo "  make test       - Executa todos os testes unitários e de integração"
	@echo "  make migrate    - Aplica as migrações Alembic no banco de dados"
	@echo "  make build      - Reconstrói os contêineres Docker"

up:
	docker compose up --build

down:
	docker compose down

test:
	pytest packages/tri_core/tests services/api/tests services/worker/tests pipelines/inep/tests -v

test-tri:
	pytest packages/tri_core/tests -v

test-api:
	pytest services/api/tests -v

test-worker:
	pytest services/worker/tests -v

test-inep:
	pytest pipelines/inep/tests -v

migrate:
	cd services/api && alembic upgrade head

build:
	docker compose build
