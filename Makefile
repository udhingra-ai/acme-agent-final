.PHONY: up down logs eval demo verify clean

## Start the full stack (build if needed)
up:
	docker compose up --build -d

## Stop all containers
down:
	docker compose down

## Tail app logs (Ctrl-C to exit)
logs:
	docker compose logs -f app

## Run the evaluation harness
eval:
	pip install -q -r evals/requirements.txt
	python evals/runner.py

## Show container status and open the UI URL
demo:
	@docker compose ps
	@echo ""
	@echo "UI (HTTPS):   https://localhost        ← primary (accept cert warning)"
	@echo "UI (HTTP):    http://localhost:8000     ← direct / eval harness"
	@echo "API docs:     http://localhost:8000/docs"
	@echo "MCP registry: http://localhost:8100/tools"
	@echo "Keycloak:     http://localhost:8080  (admin / admin)"

## Verify TLS and Redis AUTH are working
verify:
	@echo "--- TLS: HTTPS endpoint ---"
	curl -sk https://localhost/health | python3 -m json.tool
	@echo ""
	@echo "--- Redis: unauthenticated access (should fail) ---"
	-docker exec acme-redis redis-cli PING
	@echo ""
	@echo "--- Redis: authenticated access (should return PONG) ---"
	docker exec acme-redis redis-cli -a acme-redis-local PING
	@echo ""
	@echo "--- App query via HTTPS ---"
	curl -sk -X POST https://localhost/query \
	  -H 'Content-Type: application/json' \
	  -H 'x-role: sales_user' \
	  -H 'x-user: verify.user' \
	  -d '{"user_query":"Give me customer profile for Client X","session_id":"verify-tls"}' \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status: OK, tools called:', [s['tool'] for s in d.get('steps',[]) if s.get('tool')])"

## Stop containers and remove volumes
clean:
	docker compose down -v
