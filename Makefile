.PHONY: setup setup-swap up up-prod down logs backup restore rebuild status clean

setup:
	@bash scripts/setup-env.sh
	@echo ""
	@echo "Environment configured. Run 'make up' to start services."

setup-swap:
	@echo "Setting up swap (requires root)..."
	@sudo bash scripts/setup-swap.sh

up:
	docker compose up -d --build

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

backup:
	@bash scripts/backup.sh

restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backups/quant_db_YYYYMMDD_HHMMSS.sql.gz"; exit 1; fi
	@bash scripts/restore.sh "$(FILE)"

rebuild:
	docker compose down
	docker compose up -d --build

status:
	@docker compose ps
	@echo ""
	@echo "Health:"
	@docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())" 2>/dev/null || echo "Backend not responding"

clean:
	@echo "WARNING: This will remove all data (database, redis, keys)."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v
	@echo "All volumes removed."
