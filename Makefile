.PHONY: install dev dev-api build evals smoke

install:
	npm install
	python3 -m venv .venv && . .venv/bin/activate && pip install -r services/api/requirements.txt

dev:
	npm run dev

dev-api:
	. .venv/bin/activate && uvicorn app.main:app --reload --port 8000 --app-dir services/api

build:
	npm run build

evals:
	npm run test --workspace=@anna/evals

smoke:
	cd projects/04-sentiment-bench && python3 -m verdict.run_benchmark --smoke
	cd projects/05-forecast-bench && python3 -m horizon.run_benchmark --smoke
	cd projects/03-research-digest && python3 -m signal_desk.run --once
