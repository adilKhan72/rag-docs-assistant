.PHONY: up down ingest test

up:
	docker compose up --build -d

down:
	docker compose down

# Index the sample handbook in corpus/
ingest:
	docker compose exec api python -m ragdocs.cli ingest corpus --prune

# Integration tests need PostgreSQL with pgvector (started on a throwaway network).
test:
	docker network create rag-test >/dev/null 2>&1 || true
	docker run -d --rm --name rag-test-pg --network rag-test -e POSTGRES_USER=rag -e POSTGRES_PASSWORD=rag -e POSTGRES_DB=rag pgvector/pgvector:pg17 >/dev/null
	sleep 5
	docker run --rm --network rag-test -e PYTHONDONTWRITEBYTECODE=1 -e DATABASE_URL=postgresql://rag:rag@rag-test-pg:5432/rag \
		-v "$$PWD":/app -w /app python:3.12-slim sh -c 'pip install -q -r requirements.txt && python -m pytest -q -p no:cacheprovider'; \
		status=$$?; docker stop rag-test-pg >/dev/null; exit $$status
